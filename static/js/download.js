/**
 * Download Module (A4-下載導出界面)
 * Handles file download functionality for generated meeting minutes
 */

class DownloadManager {
    constructor() {
        this.downloadSection = document.getElementById('downloadSection');
        this.downloadWordBtn = document.getElementById('downloadWord');
        this.downloadPdfBtn = document.getElementById('downloadPdf');
        this.currentProcessId = null;
    }

    /**
     * Initialize download section with process ID
     * @param {string} processId - Process ID for the generated files
     */
    initializeDownloads(processId) {
        this.currentProcessId = processId;
        this.showDownloadSection();
        this.setupDownloadHandlers();
    }

    /**
     * Show download section
     */
    showDownloadSection() {
        if (this.downloadSection) {
            this.downloadSection.style.display = 'block';
            this.downloadSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    /**
     * Hide download section
     */
    hideDownloadSection() {
        if (this.downloadSection) {
            this.downloadSection.style.display = 'none';
        }
    }

    /**
     * Set up download button event handlers
     */
    setupDownloadHandlers() {
        if (this.downloadWordBtn) {
            this.downloadWordBtn.onclick = () => this.downloadFile('word');
        }
        
        if (this.downloadPdfBtn) {
            this.downloadPdfBtn.onclick = () => this.downloadFile('pdf');
        }
    }

    /**
     * Download file by type
     * @param {string} fileType - Type of file to download ('word' or 'pdf')
     */
    async downloadFile(fileType) {
        if (!this.currentProcessId) {
            this.showError('No process ID available for download');
            return;
        }

        try {
            this.setDownloadButtonState(fileType, 'downloading');
            
            const response = await fetch(`/api/download/${this.currentProcessId}/${fileType}`, {
                method: 'GET',
                headers: {
                    'Accept': fileType === 'word' ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/pdf'
                }
            });

            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }

            // Get filename from Content-Disposition header or generate default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = this.extractFilename(contentDisposition, fileType);

            // Download the file
            const blob = await response.blob();
            this.triggerDownload(blob, filename);
            
            this.setDownloadButtonState(fileType, 'completed');
            this.showSuccess(`${fileType.toUpperCase()} file downloaded successfully!`);

        } catch (error) {
            console.error(`${fileType} download failed:`, error);
            this.setDownloadButtonState(fileType, 'error');
            this.showError(`Failed to download ${fileType.toUpperCase()} file: ${error.message}`);
        }
    }

    /**
     * Extract filename from Content-Disposition header
     * @param {string} contentDisposition - Content-Disposition header value
     * @param {string} fileType - File type for fallback naming
     * @returns {string} - Extracted or generated filename
     */
    extractFilename(contentDisposition, fileType) {
        if (contentDisposition && contentDisposition.includes('filename=')) {
            const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (matches && matches[1]) {
                return matches[1].replace(/['"]/g, '');
            }
        }
        
        // Generate default filename with timestamp
        const timestamp = new Date().toISOString().split('T')[0];
        const extension = fileType === 'word' ? 'docx' : 'pdf';
        return `meeting_minutes_${timestamp}.${extension}`;
    }

    /**
     * Trigger file download in browser
     * @param {Blob} blob - File blob data
     * @param {string} filename - File name
     */
    triggerDownload(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    /**
     * Set download button state
     * @param {string} fileType - File type ('word' or 'pdf')
     * @param {string} state - Button state ('normal', 'downloading', 'completed', 'error')
     */
    setDownloadButtonState(fileType, state) {
        const button = fileType === 'word' ? this.downloadWordBtn : this.downloadPdfBtn;
        if (!button) return;

        // Reset classes
        button.classList.remove('downloading', 'completed', 'error');
        
        switch (state) {
            case 'downloading':
                button.classList.add('downloading');
                button.textContent = `Downloading ${fileType.toUpperCase()}...`;
                button.disabled = true;
                break;
                
            case 'completed':
                button.classList.add('completed');
                button.textContent = `✓ ${fileType.toUpperCase()} Downloaded`;
                button.disabled = false;
                // Reset after 3 seconds
                setTimeout(() => {
                    this.resetDownloadButton(fileType);
                }, 3000);
                break;
                
            case 'error':
                button.classList.add('error');
                button.textContent = `❌ ${fileType.toUpperCase()} Failed`;
                button.disabled = false;
                // Reset after 5 seconds
                setTimeout(() => {
                    this.resetDownloadButton(fileType);
                }, 5000);
                break;
                
            default:
                button.textContent = fileType === 'word' ? '📄 Download Word' : '📋 Download PDF';
                button.disabled = false;
        }
    }

    /**
     * Reset download button to normal state
     * @param {string} fileType - File type ('word' or 'pdf')
     */
    resetDownloadButton(fileType) {
        this.setDownloadButtonState(fileType, 'normal');
    }

    /**
     * Check if files are ready for download
     * @param {string} processId - Process ID to check
     * @returns {Promise<Object>} - Download status
     */
    async checkDownloadStatus(processId) {
        try {
            const response = await fetch(`/api/download/${processId}/status`);
            const data = await response.json();
            
            return {
                success: data.success,
                wordReady: data.files && data.files.word,
                pdfReady: data.files && data.files.pdf,
                message: data.message
            };
        } catch (error) {
            console.error('Download status check failed:', error);
            return {
                success: false,
                wordReady: false,
                pdfReady: false,
                message: 'Failed to check download status'
            };
        }
    }

    /**
     * Update download buttons based on file availability
     * @param {Object} status - Download status object
     */
    updateDownloadAvailability(status) {
        if (this.downloadWordBtn) {
            this.downloadWordBtn.disabled = !status.wordReady;
            this.downloadWordBtn.classList.toggle('unavailable', !status.wordReady);
        }
        
        if (this.downloadPdfBtn) {
            this.downloadPdfBtn.disabled = !status.pdfReady;
            this.downloadPdfBtn.classList.toggle('unavailable', !status.pdfReady);
        }
    }

    /**
     * Show success message
     * @param {string} message - Success message
     */
    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        this.showMessage(message, 'error');
    }

    /**
     * Show message to user
     * @param {string} message - Message text
     * @param {string} type - Message type ('success' or 'error')
     */
    showMessage(message, type) {
        // Create or get message element
        let messageElement = document.getElementById('downloadMessage');
        if (!messageElement) {
            messageElement = document.createElement('div');
            messageElement.id = 'downloadMessage';
            messageElement.className = 'download-message';
            this.downloadSection.appendChild(messageElement);
        }
        
        messageElement.className = `download-message ${type}`;
        messageElement.textContent = message;
        messageElement.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            messageElement.style.display = 'none';
        }, 5000);
    }

    /**
     * Reset download manager
     */
    reset() {
        this.currentProcessId = null;
        this.hideDownloadSection();
        
        // Reset button states
        this.resetDownloadButton('word');
        this.resetDownloadButton('pdf');
        
        // Hide any messages
        const messageElement = document.getElementById('downloadMessage');
        if (messageElement) {
            messageElement.style.display = 'none';
        }
    }
}

// Create global download manager instance
window.downloadManager = new DownloadManager();
/**
 * Progress Display Module (A2-處理進度展示)
 * Handles real-time progress visualization for meeting minutes generation
 */

class ProgressManager {
    constructor() {
        this.progressContainer = document.getElementById('progressContainer');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.currentProgress = 0;
        this.updateInterval = null;
    }

    /**
     * Initialize progress tracking
     * @param {string} processId - Unique process ID for tracking
     */
    startProgress(processId) {
        this.currentProgress = 0;
        this.showProgress();
        this.updateProgress(5, 'Starting AI processing...');
        
        // Start polling for progress updates
        this.updateInterval = setInterval(() => {
            this.checkProgressStatus(processId);
        }, 1000);
    }

    /**
     * Show progress container
     */
    showProgress() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
        }
    }

    /**
     * Hide progress container
     */
    hideProgress() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'none';
        }
        this.clearInterval();
    }

    /**
     * Update progress bar and text
     * @param {number} percentage - Progress percentage (0-100)
     * @param {string} message - Status message
     */
    updateProgress(percentage, message) {
        this.currentProgress = Math.min(percentage, 100);
        
        if (this.progressFill) {
            this.progressFill.style.width = this.currentProgress + '%';
        }
        
        if (this.progressText) {
            this.progressText.textContent = message || `Processing... ${this.currentProgress}%`;
        }
    }

    /**
     * Check progress status from server
     * @param {string} processId - Process ID to check
     */
    async checkProgressStatus(processId) {
        try {
            const response = await fetch(`/api/process/${processId}/status`);
            const data = await response.json();
            
            if (data.success) {
                this.updateProgress(data.progress, data.message);
                
                // If processing is complete
                if (data.progress >= 100 || data.status === 'completed') {
                    this.completeProgress(data.message || 'Processing completed!');
                } else if (data.status === 'error') {
                    this.errorProgress(data.message || 'Processing failed');
                }
            }
        } catch (error) {
            console.error('Progress check failed:', error);
            this.errorProgress('Failed to check progress status');
        }
    }

    /**
     * Mark progress as completed
     * @param {string} message - Completion message
     */
    completeProgress(message) {
        this.updateProgress(100, message);
        this.clearInterval();
        
        // Hide progress after 2 seconds
        setTimeout(() => {
            this.hideProgress();
        }, 2000);
    }

    /**
     * Mark progress as failed
     * @param {string} message - Error message
     */
    errorProgress(message) {
        this.updateProgress(this.currentProgress, `❌ ${message}`);
        this.clearInterval();
        
        // Style progress bar as error
        if (this.progressFill) {
            this.progressFill.style.backgroundColor = '#ff4444';
        }
    }

    /**
     * Clear progress update interval
     */
    clearInterval() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Reset progress to initial state
     */
    reset() {
        this.clearInterval();
        this.currentProgress = 0;
        this.hideProgress();
        
        // Reset progress bar style
        if (this.progressFill) {
            this.progressFill.style.width = '0%';
            this.progressFill.style.backgroundColor = '#007AFF';
        }
        
        if (this.progressText) {
            this.progressText.textContent = '';
        }
    }
}

// Create global progress manager instance
window.progressManager = new ProgressManager();
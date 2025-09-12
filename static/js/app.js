// Global variables
let currentFileId = null;
let processCheckInterval = null;

// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const generateSection = document.getElementById('generate-section');
const downloadSection = document.getElementById('download-section');
const generateButton = document.getElementById('generateButton');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const downloadWord = document.getElementById('downloadWord');
const downloadPdf = document.getElementById('downloadPdf');
const resetButton = document.getElementById('resetButton');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // Generate button
    generateButton.addEventListener('click', handleGenerate);
    
    // Reset button
    resetButton.addEventListener('click', handleReset);
}

function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        processFile(file);
    }
}

function processFile(file) {
    // Validate file type
    const allowedTypes = ['text/plain'];
    if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.txt')) {
        showError('Please select a .txt text file');
        return;
    }
    
    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size cannot exceed 10MB');
        return;
    }
    
    // Show file info
    fileName.textContent = file.name;
    fileSize.textContent = `File size: ${formatFileSize(file.size)}`;
    fileInfo.style.display = 'block';
    
    // Show generate section
    generateSection.style.display = 'block';
    generateSection.classList.add('slide-in');
    
    // Store file for upload
    window.selectedFile = file;
}

async function handleGenerate() {
    if (!window.selectedFile) {
        showError('Please select a file first');
        return;
    }
    
    generateButton.disabled = true;
    generateButton.textContent = 'Uploading...';
    
    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', window.selectedFile);
        
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const uploadResult = await uploadResponse.json();
        currentFileId = uploadResult.file_id;
        
        // Start generation
        const generateResponse = await fetch(`/api/generate/${currentFileId}`, {
            method: 'POST'
        });
        
        if (!generateResponse.ok) {
            const error = await generateResponse.json();
            throw new Error(error.detail || 'Generation failed');
        }
        
        // Show progress and start monitoring
        showProgress();
        startProcessMonitoring();
        
    } catch (error) {
        console.error('Generation error:', error);
        showError(error.message || 'Processing failed, please try again');
        resetGenerateButton();
    }
}

function showProgress() {
    progressContainer.style.display = 'block';
    generateButton.style.display = 'none';
    
    progressFill.style.width = '10%';
    progressText.textContent = 'Starting processing...';
}

function startProcessMonitoring() {
    if (processCheckInterval) {
        clearInterval(processCheckInterval);
    }
    
    processCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentFileId}`);
            if (!response.ok) {
                throw new Error('Unable to get processing status');
            }
            
            const status = await response.json();
            updateProgress(status);
            
            if (status.status === 'completed') {
                clearInterval(processCheckInterval);
                showDownloadSection();
            } else if (status.status === 'failed') {
                clearInterval(processCheckInterval);
                showError(status.error || 'Processing failed');
                resetGenerateButton();
            }
            
        } catch (error) {
            console.error('Status check error:', error);
            clearInterval(processCheckInterval);
            showError('Unable to get processing status');
            resetGenerateButton();
        }
    }, 2000); // Check every 2 seconds
}

function updateProgress(status) {
    const progress = status.progress || 0;
    progressFill.style.width = `${progress}%`;
    
    const statusMessages = {
        'processing': 'Processing...',
        'uploading': 'Uploading...',
        'extracting': 'AI analyzing...',
        'generating': 'Generating document...',
        'completed': 'Processing complete!'
    };
    
    progressText.textContent = statusMessages[status.status] || `Processing... ${progress}%`;
}

function showDownloadSection() {
    downloadSection.style.display = 'block';
    downloadSection.classList.add('slide-in');
    
    // Setup download links
    downloadWord.href = `/api/download/word/${currentFileId}`;
    downloadWord.style.display = 'inline-block';
    
    // For now, hide PDF download as it's not implemented
    // downloadPdf.href = `/api/download/pdf/${currentFileId}`;
    // downloadPdf.style.display = 'inline-block';
    
    showSuccess();
}

function handleReset() {
    // Reset all states
    currentFileId = null;
    window.selectedFile = null;
    
    if (processCheckInterval) {
        clearInterval(processCheckInterval);
        processCheckInterval = null;
    }
    
    // Reset UI
    fileInput.value = '';
    fileInfo.style.display = 'none';
    generateSection.style.display = 'none';
    downloadSection.style.display = 'none';
    progressContainer.style.display = 'none';
    
    resetGenerateButton();
    hideError();
    hideSuccess();
}

function resetGenerateButton() {
    generateButton.disabled = false;
    generateButton.textContent = '🚀 Start Generate Meeting Minutes';
    generateButton.style.display = 'block';
    progressContainer.style.display = 'none';
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.classList.add('fade-in');
}

function hideError() {
    errorMessage.style.display = 'none';
    errorMessage.classList.remove('fade-in');
}

function showSuccess() {
    successMessage.style.display = 'block';
    successMessage.classList.add('fade-in');
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        hideSuccess();
    }, 3000);
}

function hideSuccess() {
    successMessage.style.display = 'none';
    successMessage.classList.remove('fade-in');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Expose functions for HTML onclick handlers
window.hideError = hideError;
window.hideSuccess = hideSuccess;
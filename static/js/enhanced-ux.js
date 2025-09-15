/**
 * Enhanced UX Components
 * Improved visual guidance, error handling, and user feedback
 * Implements ICE principles - Intuitive, Concise, Encompassing
 */

class EnhancedUX {
    constructor() {
        this.notifications = [];
        this.currentStep = 1;
        this.totalSteps = 3;
        this.init();
    }

    init() {
        this.createNotificationContainer();
        this.createProgressIndicator();
        this.createTooltipSystem();
        this.enhanceExistingElements();
        this.setupKeyboardNavigation();
    }

    /**
     * Enhanced Notification System
     */
    createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        container.innerHTML = `
            <style>
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    max-width: 400px;
                }

                .notification {
                    background: white;
                    border-radius: 12px;
                    padding: 16px 20px;
                    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
                    border-left: 4px solid;
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    transform: translateX(400px);
                    opacity: 0;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                }

                .notification.show {
                    transform: translateX(0);
                    opacity: 1;
                }

                .notification.success {
                    border-left-color: #10b981;
                }

                .notification.error {
                    border-left-color: #ef4444;
                }

                .notification.warning {
                    border-left-color: #f59e0b;
                }

                .notification.info {
                    border-left-color: #3b82f6;
                }

                .notification-icon {
                    font-size: 20px;
                    flex-shrink: 0;
                    margin-top: 2px;
                }

                .notification-content {
                    flex: 1;
                }

                .notification-title {
                    font-weight: 600;
                    margin-bottom: 4px;
                    color: #1f2937;
                }

                .notification-message {
                    color: #6b7280;
                    font-size: 14px;
                    line-height: 1.4;
                }

                .notification-close {
                    background: none;
                    border: none;
                    color: #9ca3af;
                    cursor: pointer;
                    font-size: 18px;
                    padding: 0;
                    margin-left: 8px;
                    flex-shrink: 0;
                }

                .notification-close:hover {
                    color: #6b7280;
                }

                .notification-actions {
                    margin-top: 12px;
                    display: flex;
                    gap: 8px;
                }

                .notification-action {
                    padding: 4px 12px;
                    border-radius: 6px;
                    border: none;
                    font-size: 12px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .notification-action.primary {
                    background: #3b82f6;
                    color: white;
                }

                .notification-action.secondary {
                    background: #f3f4f6;
                    color: #6b7280;
                }

                .notification-action:hover {
                    transform: translateY(-1px);
                }
            </style>
        `;
        document.body.appendChild(container);
    }

    showNotification(type, title, message, actions = []) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const id = Date.now().toString();
        notification.dataset.id = id;

        notification.innerHTML = `
            <div class="notification-icon">${icons[type]}</div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
                ${actions.length > 0 ? `
                    <div class="notification-actions">
                        ${actions.map(action => `
                            <button class="notification-action ${action.style || 'secondary'}"
                                    onclick="${action.onClick}">
                                ${action.text}
                            </button>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
            <button class="notification-close" onclick="enhancedUX.hideNotification('${id}')">&times;</button>
        `;

        const container = document.getElementById('notification-container');
        container.appendChild(notification);

        // Show notification with animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Auto-hide after 5 seconds unless it's an error
        if (type !== 'error') {
            setTimeout(() => {
                this.hideNotification(id);
            }, 5000);
        }

        this.notifications.push({ id, element: notification, type });
        return id;
    }

    hideNotification(id) {
        const notification = document.querySelector(`[data-id="${id}"]`);
        if (notification) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
                this.notifications = this.notifications.filter(n => n.id !== id);
            }, 300);
        }
    }

    /**
     * Enhanced Progress Indicator
     */
    createProgressIndicator() {
        const existingHeader = document.querySelector('.header');
        const progressIndicator = document.createElement('div');
        progressIndicator.className = 'enhanced-progress-indicator';
        progressIndicator.innerHTML = `
            <style>
                .enhanced-progress-indicator {
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 15px;
                    padding: 20px;
                    margin-top: 20px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                }

                .progress-steps {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    position: relative;
                    margin-bottom: 15px;
                }

                .progress-step {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    position: relative;
                    z-index: 2;
                }

                .progress-step-circle {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: #e5e7eb;
                    border: 3px solid #e5e7eb;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    transition: all 0.3s ease;
                    color: #9ca3af;
                }

                .progress-step.active .progress-step-circle {
                    background: #3b82f6;
                    border-color: #3b82f6;
                    color: white;
                    transform: scale(1.1);
                }

                .progress-step.completed .progress-step-circle {
                    background: #10b981;
                    border-color: #10b981;
                    color: white;
                }

                .progress-step-label {
                    margin-top: 8px;
                    font-size: 12px;
                    font-weight: 500;
                    text-align: center;
                    color: #6b7280;
                    max-width: 80px;
                }

                .progress-step.active .progress-step-label {
                    color: #3b82f6;
                    font-weight: 600;
                }

                .progress-step.completed .progress-step-label {
                    color: #10b981;
                }

                .progress-line {
                    position: absolute;
                    top: 20px;
                    left: 40px;
                    right: 40px;
                    height: 3px;
                    background: #e5e7eb;
                    z-index: 1;
                }

                .progress-line-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #10b981, #3b82f6);
                    width: 0%;
                    transition: width 0.5s ease;
                    border-radius: 2px;
                }

                .progress-description {
                    text-align: center;
                    color: #6b7280;
                    font-size: 14px;
                }
            </style>

            <div class="progress-steps">
                <div class="progress-line">
                    <div class="progress-line-fill" id="progressLineFill"></div>
                </div>
                <div class="progress-step active" data-step="1">
                    <div class="progress-step-circle">1</div>
                    <div class="progress-step-label">Upload File</div>
                </div>
                <div class="progress-step" data-step="2">
                    <div class="progress-step-circle">2</div>
                    <div class="progress-step-label">AI Processing</div>
                </div>
                <div class="progress-step" data-step="3">
                    <div class="progress-step-circle">3</div>
                    <div class="progress-step-label">Download Results</div>
                </div>
            </div>
            <div class="progress-description" id="progressDescription">
                Select a meeting transcript file to begin
            </div>
        `;

        existingHeader.appendChild(progressIndicator);
    }

    updateProgress(step, description = '') {
        this.currentStep = step;

        // Update step indicators
        document.querySelectorAll('.progress-step').forEach((stepEl, index) => {
            const stepNumber = index + 1;
            stepEl.classList.remove('active', 'completed');

            if (stepNumber < step) {
                stepEl.classList.add('completed');
                stepEl.querySelector('.progress-step-circle').innerHTML = '✓';
            } else if (stepNumber === step) {
                stepEl.classList.add('active');
                stepEl.querySelector('.progress-step-circle').innerHTML = stepNumber;
            } else {
                stepEl.querySelector('.progress-step-circle').innerHTML = stepNumber;
            }
        });

        // Update progress line
        const progressPercentage = ((step - 1) / (this.totalSteps - 1)) * 100;
        const progressLineFill = document.getElementById('progressLineFill');
        if (progressLineFill) {
            progressLineFill.style.width = `${progressPercentage}%`;
        }

        // Update description
        const progressDescription = document.getElementById('progressDescription');
        if (progressDescription && description) {
            progressDescription.textContent = description;
        }
    }

    /**
     * Enhanced Tooltip System
     */
    createTooltipSystem() {
        const style = document.createElement('style');
        style.textContent = `
            .tooltip {
                position: relative;
                display: inline-block;
            }

            .tooltip-content {
                visibility: hidden;
                opacity: 0;
                position: absolute;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                background: #1f2937;
                color: white;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 12px;
                white-space: nowrap;
                z-index: 1000;
                transition: all 0.2s ease;
                pointer-events: none;
            }

            .tooltip-content::after {
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 5px solid transparent;
                border-top-color: #1f2937;
            }

            .tooltip:hover .tooltip-content {
                visibility: visible;
                opacity: 1;
            }
        `;
        document.head.appendChild(style);
    }

    addTooltip(element, text) {
        element.classList.add('tooltip');
        const tooltipContent = document.createElement('div');
        tooltipContent.className = 'tooltip-content';
        tooltipContent.textContent = text;
        element.appendChild(tooltipContent);
    }

    /**
     * Enhanced Visual Guidance
     */
    enhanceExistingElements() {
        // Add helpful tooltips
        const uploadButton = document.querySelector('.upload-button');
        if (uploadButton) {
            this.addTooltip(uploadButton, 'Click to select a .txt meeting transcript file');
        }

        const generateButton = document.getElementById('generateButton');
        if (generateButton) {
            this.addTooltip(generateButton, 'Click to start AI processing of your meeting transcript');
        }

        // Add loading states
        this.createLoadingStates();

        // Add file validation feedback
        this.enhanceFileValidation();
    }

    createLoadingStates() {
        const style = document.createElement('style');
        style.textContent = `
            .loading {
                position: relative;
                pointer-events: none;
                opacity: 0.8;
            }

            .loading::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #3b82f6;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: translate(-50%, -50%) rotate(0deg); }
                100% { transform: translate(-50%, -50%) rotate(360deg); }
            }

            .pulse {
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
        `;
        document.head.appendChild(style);
    }

    setLoading(element, isLoading) {
        if (isLoading) {
            element.classList.add('loading');
            element.setAttribute('disabled', true);
        } else {
            element.classList.remove('loading');
            element.removeAttribute('disabled');
        }
    }

    enhanceFileValidation() {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.validateFileWithFeedback(file);
                }
            });
        }
    }

    validateFileWithFeedback(file) {
        const validations = [
            {
                test: () => file.type === 'text/plain' || file.name.toLowerCase().endsWith('.txt'),
                message: 'File type validation',
                successMsg: 'Valid text file format',
                errorMsg: 'Please select a .txt file'
            },
            {
                test: () => file.size <= 10 * 1024 * 1024,
                message: 'File size validation',
                successMsg: `File size OK (${this.formatFileSize(file.size)})`,
                errorMsg: 'File too large (max 10MB)'
            },
            {
                test: () => file.size > 0,
                message: 'File content validation',
                successMsg: 'File contains data',
                errorMsg: 'File is empty'
            }
        ];

        let allValid = true;
        validations.forEach(validation => {
            if (validation.test()) {
                this.showNotification('success', validation.message, validation.successMsg);
            } else {
                this.showNotification('error', validation.message, validation.errorMsg);
                allValid = false;
            }
        });

        if (allValid) {
            this.updateProgress(2, 'File ready for processing');
        }

        return allValid;
    }

    /**
     * Keyboard Navigation
     */
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // ESC to close notifications
            if (e.key === 'Escape') {
                this.notifications.forEach(notification => {
                    this.hideNotification(notification.id);
                });
            }

            // Enter to proceed with current step
            if (e.key === 'Enter' && !e.ctrlKey && !e.altKey) {
                this.handleEnterKey();
            }
        });
    }

    handleEnterKey() {
        if (this.currentStep === 1) {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.click();
        } else if (this.currentStep === 2) {
            const generateButton = document.getElementById('generateButton');
            if (generateButton && !generateButton.disabled) generateButton.click();
        }
    }

    /**
     * Utility Methods
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Enhanced Error Handling
     */
    showEnhancedError(error, context = {}) {
        let title = 'Error Occurred';
        let message = error.message || error;
        let actions = [];

        // Contextual error messages
        if (context.type === 'upload') {
            title = 'Upload Failed';
            if (error.status === 413) {
                message = 'File too large. Please select a file smaller than 10MB.';
            } else if (error.status === 400) {
                message = 'Invalid file format. Please select a .txt file.';
            }
            actions = [
                {
                    text: 'Try Again',
                    style: 'primary',
                    onClick: 'document.getElementById("fileInput").click()'
                }
            ];
        } else if (context.type === 'processing') {
            title = 'Processing Failed';
            message = 'AI processing encountered an error. Please try again or contact support.';
            actions = [
                {
                    text: 'Retry',
                    style: 'primary',
                    onClick: 'handleGenerate()'
                },
                {
                    text: 'Start Over',
                    style: 'secondary',
                    onClick: 'handleReset()'
                }
            ];
        }

        return this.showNotification('error', title, message, actions);
    }

    showSuccess(message, actions = []) {
        return this.showNotification('success', 'Success!', message, actions);
    }

    showWarning(message, actions = []) {
        return this.showNotification('warning', 'Warning', message, actions);
    }

    showInfo(message, actions = []) {
        return this.showNotification('info', 'Information', message, actions);
    }
}

// Initialize enhanced UX system
const enhancedUX = new EnhancedUX();

// Export for global use
window.enhancedUX = enhancedUX;
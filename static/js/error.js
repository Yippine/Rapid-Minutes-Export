/**
 * Error Handling Module (U06-錯誤處理與用戶反饋界面)
 * Provides comprehensive error handling and user feedback system
 */

class ErrorManager {
    constructor() {
        this.errorContainer = null;
        this.initializeErrorContainer();
        this.setupGlobalErrorHandlers();
    }

    /**
     * Initialize error display container
     */
    initializeErrorContainer() {
        // Create error container if it doesn't exist
        this.errorContainer = document.getElementById('errorContainer');
        if (!this.errorContainer) {
            this.errorContainer = document.createElement('div');
            this.errorContainer.id = 'errorContainer';
            this.errorContainer.className = 'error-container';
            document.body.appendChild(this.errorContainer);
        }
    }

    /**
     * Set up global error handlers
     */
    setupGlobalErrorHandlers() {
        // Handle uncaught JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.showError('An unexpected error occurred. Please try again.', 'system');
        });

        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            this.showError('A network or processing error occurred. Please check your connection and try again.', 'network');
        });
    }

    /**
     * Show error message to user
     * @param {string} message - Error message to display
     * @param {string} type - Error type ('validation', 'network', 'server', 'system')
     * @param {Object} options - Additional options
     */
    showError(message, type = 'general', options = {}) {
        const errorElement = this.createErrorElement(message, type, options);
        this.displayError(errorElement);
        
        // Log error for debugging
        console.error(`${type.toUpperCase()} Error:`, message, options);
    }

    /**
     * Create error element
     * @param {string} message - Error message
     * @param {string} type - Error type
     * @param {Object} options - Additional options
     * @returns {HTMLElement} - Error element
     */
    createErrorElement(message, type, options) {
        const errorDiv = document.createElement('div');
        errorDiv.className = `error-message error-${type}`;
        
        // Add icon based on error type
        const icon = this.getErrorIcon(type);
        
        // Create error content
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-icon">${icon}</span>
                <div class="error-details">
                    <div class="error-text">${message}</div>
                    ${options.details ? `<div class="error-description">${options.details}</div>` : ''}
                    ${options.actions ? this.createErrorActions(options.actions) : ''}
                </div>
                <button class="error-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        // Auto-dismiss after timeout (unless it's a critical error)
        if (!options.persistent && type !== 'critical') {
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, options.timeout || 5000);
        }

        return errorDiv;
    }

    /**
     * Get appropriate icon for error type
     * @param {string} type - Error type
     * @returns {string} - Icon emoji or character
     */
    getErrorIcon(type) {
        const icons = {
            validation: '⚠️',
            network: '🌐',
            server: '🔧',
            system: '💻',
            upload: '📄',
            processing: '⚡',
            download: '📥',
            critical: '🚨',
            general: '❌'
        };
        return icons[type] || icons.general;
    }

    /**
     * Create error action buttons
     * @param {Array} actions - Array of action objects
     * @returns {string} - HTML for action buttons
     */
    createErrorActions(actions) {
        if (!actions || actions.length === 0) return '';
        
        const buttonHTML = actions.map(action => 
            `<button class="error-action" onclick="${action.handler}">${action.label}</button>`
        ).join('');
        
        return `<div class="error-actions">${buttonHTML}</div>`;
    }

    /**
     * Display error in container
     * @param {HTMLElement} errorElement - Error element to display
     */
    displayError(errorElement) {
        this.errorContainer.appendChild(errorElement);
        
        // Animate in
        requestAnimationFrame(() => {
            errorElement.classList.add('show');
        });

        // Scroll to error if not in viewport
        setTimeout(() => {
            if (!this.isElementInViewport(errorElement)) {
                errorElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }, 300);
    }

    /**
     * Show validation error
     * @param {string} message - Validation error message
     * @param {string} field - Field name that failed validation
     */
    showValidationError(message, field = null) {
        const details = field ? `Please check the ${field} field.` : 'Please correct the highlighted fields.';
        this.showError(message, 'validation', {
            details: details,
            timeout: 7000
        });
    }

    /**
     * Show network error
     * @param {string} message - Network error message
     * @param {Error} error - Original error object
     */
    showNetworkError(message = 'Network connection failed', error = null) {
        const details = this.getNetworkErrorDetails(error);
        this.showError(message, 'network', {
            details: details,
            actions: [
                { label: 'Retry', handler: 'location.reload()' }
            ],
            timeout: 10000
        });
    }

    /**
     * Get network error details
     * @param {Error} error - Network error
     * @returns {string} - Error details
     */
    getNetworkErrorDetails(error) {
        if (!error) return 'Please check your internet connection and try again.';
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            return 'Unable to connect to the server. Please check your internet connection.';
        }
        
        if (error.code === 'ECONNREFUSED') {
            return 'The server is currently unavailable. Please try again later.';
        }
        
        return 'A network error occurred. Please check your connection and try again.';
    }

    /**
     * Show processing error
     * @param {string} message - Processing error message
     * @param {Object} context - Error context information
     */
    showProcessingError(message, context = {}) {
        this.showError(message, 'processing', {
            details: 'The AI processing failed. You can try uploading the file again.',
            actions: [
                { label: 'Try Again', handler: 'window.location.reload()' },
                { label: 'Upload New File', handler: 'window.resetApp && window.resetApp()' }
            ],
            timeout: 8000
        });
    }

    /**
     * Show upload error
     * @param {string} message - Upload error message
     * @param {Object} fileInfo - File information
     */
    showUploadError(message, fileInfo = {}) {
        let details = 'Please check the file and try again.';
        
        if (fileInfo.size && fileInfo.size > 10 * 1024 * 1024) {
            details = 'File size exceeds 10MB limit. Please use a smaller file.';
        } else if (fileInfo.type && !fileInfo.type.includes('text')) {
            details = 'Only text (.txt) files are supported. Please convert your file to .txt format.';
        }
        
        this.showError(message, 'upload', {
            details: details,
            timeout: 6000
        });
    }

    /**
     * Show critical error
     * @param {string} message - Critical error message
     * @param {Object} options - Error options
     */
    showCriticalError(message, options = {}) {
        this.showError(message, 'critical', {
            details: 'The application encountered a critical error. Please refresh the page.',
            actions: [
                { label: 'Refresh Page', handler: 'window.location.reload()' }
            ],
            persistent: true,
            ...options
        });
    }

    /**
     * Show success message
     * @param {string} message - Success message
     * @param {Object} options - Additional options
     */
    showSuccess(message, options = {}) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <div class="success-content">
                <span class="success-icon">✅</span>
                <div class="success-text">${message}</div>
                <button class="success-close" onclick="this.parentElement.parentElement.remove()">✕</button>
            </div>
        `;

        this.errorContainer.appendChild(successDiv);
        
        // Animate in
        requestAnimationFrame(() => {
            successDiv.classList.add('show');
        });

        // Auto-dismiss
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, options.timeout || 4000);
    }

    /**
     * Clear all error messages
     */
    clearErrors() {
        if (this.errorContainer) {
            this.errorContainer.innerHTML = '';
        }
    }

    /**
     * Check if element is in viewport
     * @param {HTMLElement} element - Element to check
     * @returns {boolean} - True if in viewport
     */
    isElementInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * Format error for logging
     * @param {Error} error - Error object
     * @param {Object} context - Additional context
     * @returns {Object} - Formatted error object
     */
    formatErrorForLogging(error, context = {}) {
        return {
            message: error.message,
            stack: error.stack,
            name: error.name,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            context: context
        };
    }
}

// Create global error manager instance
window.errorManager = new ErrorManager();

// Convenience functions for global access
window.showError = (message, type, options) => window.errorManager.showError(message, type, options);
window.showSuccess = (message, options) => window.errorManager.showSuccess(message, options);
window.clearErrors = () => window.errorManager.clearErrors();
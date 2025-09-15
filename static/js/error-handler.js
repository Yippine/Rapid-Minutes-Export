/**
 * Enhanced Error Handler
 * Provides contextual error messages and recovery suggestions
 * Implements user-friendly error communication
 */

class ErrorHandler {
    constructor() {
        this.errorLog = [];
        this.setupGlobalErrorHandling();
    }

    setupGlobalErrorHandling() {
        // Catch unhandled JavaScript errors
        window.addEventListener('error', (event) => {
            this.logError('JavaScript Error', event.error, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        // Catch unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.logError('Unhandled Promise Rejection', event.reason);
        });

        // Catch network errors
        this.setupNetworkErrorHandling();
    }

    setupNetworkErrorHandling() {
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                if (!response.ok) {
                    this.handleNetworkError(response, args[0]);
                }
                return response;
            } catch (error) {
                this.handleNetworkError(error, args[0]);
                throw error;
            }
        };
    }

    logError(type, error, context = {}) {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            type,
            error: error.toString(),
            stack: error.stack,
            context,
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        this.errorLog.push(errorEntry);
        console.error('Error logged:', errorEntry);

        // Limit log size
        if (this.errorLog.length > 50) {
            this.errorLog = this.errorLog.slice(-25);
        }
    }

    handleNetworkError(response, url) {
        const context = { url, status: response.status };

        if (response.status) {
            switch (response.status) {
                case 400:
                    this.showUserFriendlyError('Invalid Request',
                        'The request was not formatted correctly. Please check your input and try again.');
                    break;
                case 401:
                    this.showUserFriendlyError('Authentication Required',
                        'Please log in to continue.');
                    break;
                case 403:
                    this.showUserFriendlyError('Access Denied',
                        'You do not have permission to perform this action.');
                    break;
                case 404:
                    this.showUserFriendlyError('Not Found',
                        'The requested resource could not be found.');
                    break;
                case 413:
                    this.showUserFriendlyError('File Too Large',
                        'The uploaded file exceeds the 10MB size limit. Please select a smaller file.');
                    break;
                case 429:
                    this.showUserFriendlyError('Too Many Requests',
                        'Please wait a moment before trying again.');
                    break;
                case 500:
                    this.showUserFriendlyError('Server Error',
                        'A server error occurred. Please try again in a few minutes.');
                    break;
                case 502:
                case 503:
                case 504:
                    this.showUserFriendlyError('Service Unavailable',
                        'The service is temporarily unavailable. Please try again later.');
                    break;
                default:
                    this.showUserFriendlyError('Network Error',
                        `An unexpected error occurred (${response.status}). Please try again.`);
            }
        } else {
            this.showUserFriendlyError('Connection Error',
                'Unable to connect to the server. Please check your internet connection and try again.');
        }

        this.logError('Network Error', response, context);
    }

    showUserFriendlyError(title, message, actions = []) {
        if (window.enhancedUX) {
            return window.enhancedUX.showNotification('error', title, message, actions);
        } else {
            // Fallback to basic alert
            alert(`${title}: ${message}`);
        }
    }

    getContextualErrorMessage(error, operation) {
        const errorMessage = error.message || error.toString();

        // File upload errors
        if (operation === 'upload') {
            if (errorMessage.includes('size') || errorMessage.includes('large')) {
                return {
                    title: 'File Too Large',
                    message: 'The selected file is too large. Please choose a file smaller than 10MB.',
                    suggestions: [
                        'Compress your text file',
                        'Split large transcripts into smaller sections',
                        'Remove unnecessary content from the transcript'
                    ]
                };
            }

            if (errorMessage.includes('type') || errorMessage.includes('format')) {
                return {
                    title: 'Invalid File Type',
                    message: 'Only .txt files are supported for meeting transcripts.',
                    suggestions: [
                        'Convert your file to .txt format',
                        'Copy and paste text into a new .txt file',
                        'Use a plain text editor to save your content'
                    ]
                };
            }

            if (errorMessage.includes('empty')) {
                return {
                    title: 'Empty File',
                    message: 'The selected file appears to be empty.',
                    suggestions: [
                        'Check that your file contains meeting transcript text',
                        'Select a different file',
                        'Add content to your file before uploading'
                    ]
                };
            }
        }

        // AI processing errors
        if (operation === 'processing') {
            if (errorMessage.includes('timeout')) {
                return {
                    title: 'Processing Timeout',
                    message: 'AI processing took longer than expected and was cancelled.',
                    suggestions: [
                        'Try again with a shorter transcript',
                        'Check your internet connection',
                        'Split large meetings into smaller sections'
                    ]
                };
            }

            if (errorMessage.includes('model') || errorMessage.includes('AI')) {
                return {
                    title: 'AI Service Error',
                    message: 'The AI processing service is currently unavailable.',
                    suggestions: [
                        'Try again in a few minutes',
                        'Check if the AI service is running',
                        'Contact support if the problem persists'
                    ]
                };
            }

            if (errorMessage.includes('content') || errorMessage.includes('parse')) {
                return {
                    title: 'Content Processing Error',
                    message: 'The transcript content could not be processed properly.',
                    suggestions: [
                        'Check that your transcript contains meeting content',
                        'Remove special characters or formatting',
                        'Ensure the text is readable and well-formatted'
                    ]
                };
            }
        }

        // Download errors
        if (operation === 'download') {
            return {
                title: 'Download Failed',
                message: 'The file could not be downloaded.',
                suggestions: [
                    'Check your internet connection',
                    'Try downloading again',
                    'Contact support if the problem persists'
                ]
            };
        }

        // Generic error
        return {
            title: 'Unexpected Error',
            message: 'An unexpected error occurred during the operation.',
            suggestions: [
                'Try the operation again',
                'Refresh the page and start over',
                'Contact support if the problem persists'
            ]
        };
    }

    showDetailedError(error, operation) {
        const errorInfo = this.getContextualErrorMessage(error, operation);

        const actions = [
            {
                text: 'Try Again',
                style: 'primary',
                onClick: `errorHandler.retryOperation('${operation}')`
            },
            {
                text: 'Get Help',
                style: 'secondary',
                onClick: 'errorHandler.showHelp()'
            }
        ];

        if (window.enhancedUX) {
            const notificationId = window.enhancedUX.showNotification(
                'error',
                errorInfo.title,
                errorInfo.message,
                actions
            );

            // Show suggestions after a delay
            setTimeout(() => {
                if (errorInfo.suggestions.length > 0) {
                    window.enhancedUX.showNotification(
                        'info',
                        'Suggestions',
                        errorInfo.suggestions.join(' • '),
                        []
                    );
                }
            }, 2000);

            return notificationId;
        }
    }

    retryOperation(operation) {
        switch (operation) {
            case 'upload':
                document.getElementById('fileInput')?.click();
                break;
            case 'processing':
                document.getElementById('generateButton')?.click();
                break;
            case 'download':
                // Retry the last download
                break;
            default:
                window.location.reload();
        }
    }

    showHelp() {
        const helpContent = `
            <div style="text-align: left; max-width: 400px;">
                <h3>Common Issues & Solutions</h3>
                <div style="margin: 15px 0;">
                    <strong>File Upload Issues:</strong>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li>Only .txt files are supported</li>
                        <li>File size must be under 10MB</li>
                        <li>File must contain text content</li>
                    </ul>
                </div>
                <div style="margin: 15px 0;">
                    <strong>Processing Issues:</strong>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li>Ensure transcript contains meeting content</li>
                        <li>Check internet connection</li>
                        <li>Try with shorter transcripts</li>
                    </ul>
                </div>
                <div style="margin: 15px 0;">
                    <strong>Still having problems?</strong>
                    <p style="margin: 5px 0;">Contact support with error details.</p>
                </div>
            </div>
        `;

        if (window.enhancedUX) {
            window.enhancedUX.showNotification('info', 'Help & Troubleshooting', helpContent);
        }
    }

    getErrorReport() {
        return {
            errors: this.errorLog,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            url: window.location.href
        };
    }

    clearErrorLog() {
        this.errorLog = [];
    }
}

// Initialize error handler
const errorHandler = new ErrorHandler();

// Export for global use
window.errorHandler = errorHandler;
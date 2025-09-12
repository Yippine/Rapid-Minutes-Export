/**
 * Result Preview Module (A3-結果預覽界面)
 * Handles preview of generated meeting minutes before download
 */

class PreviewManager {
    constructor() {
        this.previewContainer = document.getElementById('previewContainer');
        this.previewContent = document.getElementById('previewContent');
        this.previewModal = document.getElementById('previewModal');
    }

    /**
     * Show preview of generated meeting minutes
     * @param {Object} data - Meeting minutes data
     * @param {string} processId - Process ID for the generated document
     */
    async showPreview(data, processId) {
        try {
            // Fetch preview content from server
            const response = await fetch(`/api/process/${processId}/preview`);
            const previewData = await response.json();
            
            if (previewData.success) {
                this.displayPreview(previewData.content);
                this.showPreviewModal();
            } else {
                throw new Error(previewData.message || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Preview generation failed:', error);
            this.showError('Failed to generate preview: ' + error.message);
        }
    }

    /**
     * Display preview content
     * @param {Object} content - Structured meeting minutes content
     */
    displayPreview(content) {
        if (!this.previewContent) return;

        const previewHTML = this.generatePreviewHTML(content);
        this.previewContent.innerHTML = previewHTML;
    }

    /**
     * Generate HTML for preview display
     * @param {Object} content - Meeting content data
     * @returns {string} - HTML string for preview
     */
    generatePreviewHTML(content) {
        return `
            <div class="preview-document">
                <div class="preview-header">
                    <h1>${content.meeting_title || 'Meeting Minutes'}</h1>
                    <div class="meeting-info">
                        <p><strong>Date:</strong> ${content.meeting_date || 'N/A'}</p>
                        <p><strong>Time:</strong> ${content.meeting_time || 'N/A'}</p>
                        <p><strong>Location:</strong> ${content.meeting_location || 'N/A'}</p>
                        <p><strong>Facilitator:</strong> ${content.facilitator || 'N/A'}</p>
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Attendees</h2>
                    <div class="attendees-list">
                        ${this.formatAttendees(content.attendees)}
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Meeting Agenda</h2>
                    <div class="agenda-content">
                        ${this.formatAgenda(content.agenda_items)}
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Discussion Points</h2>
                    <div class="discussion-content">
                        ${this.formatDiscussion(content.discussion_points)}
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Action Items</h2>
                    <div class="action-items">
                        ${this.formatActionItems(content.action_items)}
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Decisions Made</h2>
                    <div class="decisions-content">
                        ${this.formatDecisions(content.decisions)}
                    </div>
                </div>

                <div class="preview-section">
                    <h2>Next Meeting</h2>
                    <div class="next-meeting-info">
                        <p><strong>Date:</strong> ${content.next_meeting_date || 'TBD'}</p>
                        <p><strong>Time:</strong> ${content.next_meeting_time || 'TBD'}</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Format attendees for display
     * @param {Array} attendees - List of attendees
     * @returns {string} - HTML string for attendees
     */
    formatAttendees(attendees) {
        if (!attendees || attendees.length === 0) {
            return '<p>No attendees listed</p>';
        }
        return '<ul>' + attendees.map(attendee => `<li>${attendee}</li>`).join('') + '</ul>';
    }

    /**
     * Format agenda items for display
     * @param {Array|string} agendaItems - Agenda items
     * @returns {string} - HTML string for agenda
     */
    formatAgenda(agendaItems) {
        if (!agendaItems) return '<p>No agenda items</p>';
        
        if (typeof agendaItems === 'string') {
            return `<p>${agendaItems}</p>`;
        }
        
        if (Array.isArray(agendaItems)) {
            return '<ol>' + agendaItems.map(item => `<li>${item}</li>`).join('') + '</ol>';
        }
        
        return '<p>No agenda items</p>';
    }

    /**
     * Format discussion points for display
     * @param {Array|string} discussionPoints - Discussion content
     * @returns {string} - HTML string for discussion
     */
    formatDiscussion(discussionPoints) {
        if (!discussionPoints) return '<p>No discussion points</p>';
        
        if (typeof discussionPoints === 'string') {
            return `<div class="discussion-text">${discussionPoints}</div>`;
        }
        
        if (Array.isArray(discussionPoints)) {
            return '<ul>' + discussionPoints.map(point => `<li>${point}</li>`).join('') + '</ul>';
        }
        
        return '<p>No discussion points</p>';
    }

    /**
     * Format action items for display
     * @param {Array} actionItems - Action items with assignee and due date
     * @returns {string} - HTML string for action items
     */
    formatActionItems(actionItems) {
        if (!actionItems || actionItems.length === 0) {
            return '<p>No action items</p>';
        }
        
        let html = '<table class="action-items-table"><thead><tr><th>Task</th><th>Assignee</th><th>Due Date</th></tr></thead><tbody>';
        
        actionItems.forEach(item => {
            html += `<tr>
                <td>${item.task || item.description || 'N/A'}</td>
                <td>${item.assignee || 'Unassigned'}</td>
                <td>${item.due_date || 'TBD'}</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        return html;
    }

    /**
     * Format decisions for display
     * @param {Array|string} decisions - Meeting decisions
     * @returns {string} - HTML string for decisions
     */
    formatDecisions(decisions) {
        if (!decisions) return '<p>No decisions made</p>';
        
        if (typeof decisions === 'string') {
            return `<p>${decisions}</p>`;
        }
        
        if (Array.isArray(decisions)) {
            return '<ul>' + decisions.map(decision => `<li>${decision}</li>`).join('') + '</ul>';
        }
        
        return '<p>No decisions made</p>';
    }

    /**
     * Show preview modal
     */
    showPreviewModal() {
        if (this.previewModal) {
            this.previewModal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Hide preview modal
     */
    hidePreviewModal() {
        if (this.previewModal) {
            this.previewModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        // Create or show error element
        let errorElement = document.getElementById('previewError');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.id = 'previewError';
            errorElement.className = 'error-message';
            document.body.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

// Create global preview manager instance
window.previewManager = new PreviewManager();

// Set up modal close handlers
document.addEventListener('DOMContentLoaded', function() {
    // Close modal when clicking outside
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                window.previewManager.hidePreviewModal();
            }
        });
    }
    
    // Close modal with close button
    const closeButton = document.getElementById('previewClose');
    if (closeButton) {
        closeButton.addEventListener('click', function() {
            window.previewManager.hidePreviewModal();
        });
    }
    
    // Close modal with escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.style.display === 'block') {
            window.previewManager.hidePreviewModal();
        }
    });
});
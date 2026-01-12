// =============================================================================
// LAMAN - Main JavaScript
// =============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize message auto-dismiss
    initMessages();
});

// =============================================================================
// Messages
// =============================================================================

function initMessages() {
    const messages = document.querySelectorAll('.message');
    
    messages.forEach(function(message) {
        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            dismissMessage(message);
        }, 5000);
        
        // Close button
        const closeBtn = message.querySelector('.message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                dismissMessage(message);
            });
        }
    });
}

function dismissMessage(message) {
    message.style.opacity = '0';
    message.style.transform = 'translateY(-10px)';
    setTimeout(function() {
        message.remove();
    }, 300);
}

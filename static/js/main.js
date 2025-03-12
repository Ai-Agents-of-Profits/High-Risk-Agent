// Define chatHistory as a global variable
let chatHistory;

document.addEventListener('DOMContentLoaded', function() {
    // Check server status immediately
    checkServerStatus();
    
    // Form submission handling
    const promptForm = document.getElementById('prompt-form');
    const promptInput = document.getElementById('prompt-input');
    const submitButton = document.getElementById('submit-button');
    chatHistory = document.getElementById('chat-history'); // Assign to global variable
    
    promptForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        
        // Add user message to chat
        addMessage('user', prompt);
        
        // Clear input
        promptInput.value = '';
        
        // Disable input while processing
        promptInput.disabled = true;
        submitButton.disabled = true;
        
        // Add loading indicator
        const loadingId = addLoadingIndicator();
        
        // Send to backend
        sendPrompt(prompt)
            .then(response => {
                // Remove loading indicator
                removeLoadingIndicator(loadingId);
                
                // Add assistant response to chat
                addMessage('assistant', response.response);
                
                // Scroll to bottom
                scrollToBottom();
            })
            .catch(error => {
                // Remove loading indicator
                removeLoadingIndicator(loadingId);
                
                // Add error message
                addMessage('system', `Error: ${error.message || 'Failed to process your request'}`);
                
                console.error('Error:', error);
            })
            .finally(() => {
                // Re-enable input
                promptInput.disabled = false;
                submitButton.disabled = false;
                promptInput.focus();
            });
    });
    
    // Periodically check server status
    setInterval(checkServerStatus, 30000);
});

// Send prompt to backend
async function sendPrompt(prompt) {
    const response = await fetch('/api/prompt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt })
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to process your request');
    }
    
    return await response.json();
}

// Check server status
async function checkServerStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        // Update status indicators
        updateStatusIndicator('crypto-status', status.crypto_connected);
        updateStatusIndicator('binance-status', status.binance_connected);
        updateStatusIndicator('openai-status', status.openai_connected);
        
        // Update tool counts
        document.querySelector('#crypto-tools .tools-count').textContent = status.crypto_tools_count;
        document.querySelector('#binance-tools .tools-count').textContent = status.binance_tools_count;
    } catch (error) {
        console.error('Failed to check server status:', error);
    }
}

// Update status indicator
function updateStatusIndicator(elementId, isConnected) {
    const statusElement = document.querySelector(`#${elementId} .status-indicator`);
    
    if (isConnected) {
        statusElement.textContent = 'Connected';
        statusElement.classList.add('connected');
        statusElement.classList.remove('disconnected');
    } else {
        statusElement.textContent = 'Disconnected';
        statusElement.classList.add('disconnected');
        statusElement.classList.remove('connected');
    }
}

// Add message to chat
function addMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `${type}-message`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // For user messages, just use the text
    if (type === 'user') {
        messageContent.textContent = content;
    } 
    // For assistant and system messages, parse markdown
    else {
        messageContent.innerHTML = marked.parse(content);
    }
    
    messageDiv.appendChild(messageContent);
    
    // Add timestamp
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-time';
    timestampDiv.textContent = new Date().toLocaleTimeString();
    messageDiv.appendChild(timestampDiv);
    
    chatHistory.appendChild(messageDiv);
    
    // Scroll to bottom
    scrollToBottom();
}

// Add loading indicator
function addLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.id = id;
    
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    loadingDiv.appendChild(spinner);
    
    chatHistory.appendChild(loadingDiv);
    scrollToBottom();
    
    return id;
}

// Remove loading indicator
function removeLoadingIndicator(id) {
    const loadingElement = document.getElementById(id);
    if (loadingElement) {
        loadingElement.remove();
    }
}

// Scroll chat to bottom
function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Set suggestion
function setSuggestion(text) {
    document.getElementById('prompt-input').value = text;
    document.getElementById('prompt-input').focus();
}

function appendMessage(content, isUser = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    // Use innerHTML to render HTML tags (like <strong> for bold)
    messageDiv.innerHTML = content;
    
    document.getElementById("messages").appendChild(messageDiv);
    document.getElementById("chat-box").scrollTop = document.getElementById("chat-box").scrollHeight;
}

 function stop_ai_chat() {
        fetch('http://' + window.location.hostname + ':5001/stop_ai_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => {
            if (response.ok) {
                window.location.href = 'http://' + window.location.hostname + ':5001/';  // Redirect to kiosk home
            } else {
                console.error('Failed to stop ai_chat:', response.statusText);
            }
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }


function sendMessage() {
    const userInput = document.getElementById("user-input").value;
    if (!userInput.trim()) return;

    // Display user's message
    appendMessage(userInput, true);
    document.getElementById("user-input").value = '';

    // Send user's message to the server
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userInput })
    })
    .then(response => response.json())
    .then(data => {
        // Display bot's response
        appendMessage(data.response);
    })
    .catch(error => {
        console.error('Error:', error);
        appendMessage("Sorry, something went wrong.");
    });
}

// Press Enter to send message
document.getElementById("user-input").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

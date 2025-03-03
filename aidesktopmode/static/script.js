// Get references to the buttons and content container
const aiModeBtn = document.getElementById('aiModeBtn');
const desktopModeBtn = document.getElementById('desktopModeBtn');
const body = document.body;
const content = document.getElementById('content');

// Add event listeners to the buttons
aiModeBtn.addEventListener('click', function() {
    body.classList.remove('desktop-mode');
    body.classList.add('ai-mode');
    content.innerHTML = `<h1>AI Mode Activated</h1><p>Welcome to the AI Mode! Here we work with intelligent algorithms.</p>`;
});

desktopModeBtn.addEventListener('click', function() {
    body.classList.remove('ai-mode');
    body.classList.add('desktop-mode');
    content.innerHTML = `<h1>Desktop Mode Activated</h1><p>Welcome to the Desktop Mode! This mode simulates a desktop-like environment.</p>`;
});

// Set initial mode to Desktop Mode
body.classList.add('desktop-mode');

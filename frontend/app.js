// Configuration
// Use localhost for local testing, production URL for deployed version
const API_BASE_URL = "http://localhost:8000";
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const MODEL = "anthropic/claude-haiku-4.5";

const SYSTEM_PROMPT = `Tu es un assistant médical. Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur le contexte fourni ci-dessous. Si le contexte ne permet pas de répondre, dis-le clairement. Réponds en français, de façon claire et concise.`;

// DOM Elements
const settingsBtn = document.getElementById('settings-btn');
const statusDot = document.getElementById('status-dot');
const modalOverlay = document.getElementById('modal-overlay');
const modalClose = document.getElementById('modal-close');
const modalCancel = document.getElementById('modal-cancel');
const saveApiKeyBtn = document.getElementById('save-api-key');
const apiKeyInput = document.getElementById('api-key');
const modalStatus = document.getElementById('modal-status');
const messagesContainer = document.getElementById('messages');
const welcomeState = document.getElementById('welcome-state');
const typingIndicator = document.getElementById('typing-indicator');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const inputForm = document.getElementById('input-form');
const footer = document.getElementById('footer');

// Check for existing API key in sessionStorage on load
window.addEventListener('DOMContentLoaded', () => {
    const savedKey = sessionStorage.getItem('openrouter_api_key');
    if (savedKey) {
        apiKeyInput.value = savedKey;
        updateStatusDot(true);
        setInputEnabled(true);
    }
    setupEventListeners();
});

function setupEventListeners() {
    // Settings button - open modal
    settingsBtn.addEventListener('click', openModal);

    // Close modal
    modalClose.addEventListener('click', closeModal);
    modalCancel.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });

    // Save API key
    saveApiKeyBtn.addEventListener('click', saveApiKey);

    // Enter key in API key input
    apiKeyInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') saveApiKeyBtn.click();
    });

    // Send message (form submit)
    inputForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Enter key in user input (handled by form submit)
    // But allow Shift+Enter for new line
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Escape key to close modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modalOverlay.hidden) {
            closeModal();
        }
    });
}

function openModal() {
    modalOverlay.hidden = false;
    settingsBtn.setAttribute('aria-expanded', 'true');
    // Focus the input after modal animation
    setTimeout(() => apiKeyInput.focus(), 150);
}

function closeModal() {
    modalOverlay.hidden = true;
    settingsBtn.setAttribute('aria-expanded', 'false');
    modalStatus.textContent = '';
    modalStatus.className = 'modal-status';
}

function saveApiKey() {
    const key = apiKeyInput.value.trim();
    if (!key) {
        setModalStatus('Veuillez entrer une clé API', 'error');
        return;
    }
    if (!key.startsWith('sk-or-')) {
        setModalStatus('Format de clé invalide (doit commencer par sk-or-)', 'error');
        return;
    }
    sessionStorage.setItem('openrouter_api_key', key);
    setModalStatus('Clé enregistrée ✓', 'success');
    updateStatusDot(true);
    setTimeout(() => {
        closeModal();
        setInputEnabled(true);
        userInput.focus();
    }, 500);
}

function setModalStatus(text, type) {
    modalStatus.textContent = text;
    modalStatus.className = `modal-status ${type}`;
}

function updateStatusDot(active) {
    statusDot.classList.toggle('active', active);
}

async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;

    const apiKey = sessionStorage.getItem('openrouter_api_key');
    if (!apiKey) {
        showError('Clé API manquante. Cliquez sur l\'icône ⚙ pour l\'entrer.');
        return;
    }

    // Hide welcome state on first message
    if (welcomeState && welcomeState.parentNode) {
        welcomeState.remove();
    }

    // Add user message to chat
    addMessage(question, 'user');
    userInput.value = '';
    setLoading(true);
    setInputEnabled(false);

    try {
        // Step 1: Call /query endpoint
        const context = await fetchContext(question);

        // Step 2: Call OpenRouter
        const answer = await callOpenRouter(apiKey, question, context);

        // Add assistant response
        addMessage(answer, 'assistant');
    } catch (err) {
        // Error already displayed by fetchContext or callOpenRouter
        console.error(err);
    } finally {
        setLoading(false);
        setInputEnabled(true);
        userInput.focus();
    }
}

async function fetchContext(question) {
    try {
        const res = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: question })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        return data.context_extrait || '';
    } catch (err) {
        showError('Impossible de contacter le service de recherche');
        throw err;
    }
}

async function callOpenRouter(apiKey, question, context) {
    try {
        const res = await fetch(OPENROUTER_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: MODEL,
                messages: [
                    { role: 'system', content: SYSTEM_PROMPT },
                    { role: 'user', content: `Contexte:\n${context}\n\nQuestion: ${question}` }
                ],
                temperature: 0.3,
                max_tokens: 1000
            })
        });

        if (res.status === 401) {
            showError('Clé API invalide, vérifiez votre saisie');
            updateStatusDot(false);
            throw new Error('Invalid API key');
        }
        if (res.status === 429) {
            showError('Limite de requêtes atteinte, réessayez dans quelques instants');
            throw new Error('Rate limited');
        }
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(`OpenRouter error: ${res.status} - ${JSON.stringify(errData)}`);
        }

        const data = await res.json();
        return data.choices?.[0]?.message?.content || 'Réponse vide reçue';
    } catch (err) {
        if (err.message !== 'Invalid API key' && err.message !== 'Rate limited') {
            showError(`Erreur OpenRouter: ${err.message}`);
        }
        throw err;
    }
}

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.textContent = text;
    messagesContainer.appendChild(div);
    scrollToBottom();
}

function showError(text) {
    const div = document.createElement('div');
    div.className = 'message error';
    div.textContent = text;
    messagesContainer.appendChild(div);
    scrollToBottom();
}

function setLoading(isLoading) {
    typingIndicator.hidden = !isLoading;
    if (isLoading) {
        scrollToBottom();
    }
}

function setInputEnabled(enabled) {
    userInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
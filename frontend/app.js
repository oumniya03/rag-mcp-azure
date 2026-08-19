const API_BASE_URL = "https://rag-mcp-azure.redsand-f0795bb6.francecentral.azurecontainerapps.io";

// DOM
const messagesContainer = document.getElementById('messages');
const suggestionsRow    = document.getElementById('suggestions-row');
const typingIndicator   = document.getElementById('typing-indicator');
const userInput         = document.getElementById('user-input');
const sendBtn           = document.getElementById('send-btn');
const inputForm         = document.getElementById('input-form');

window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    lucide.createIcons();
});

function setupEventListeners() {
    inputForm.addEventListener('submit', (e) => { e.preventDefault(); sendMessage(); });
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            userInput.value = chip.textContent;
            sendMessage();
        });
    });
}

async function sendMessage() {
    const question = userInput.value.trim();
    if (!question) return;

    if (suggestionsRow) suggestionsRow.remove();

    addMessage(question, 'user');
    userInput.value = '';
    setLoading(true);
    setInputEnabled(false);

    try {
        const res = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: question })
        });

        if (res.status === 429) { showError('Trop de requêtes, réessayez dans quelques instants.'); return; }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        addMessage(data.answer || 'Réponse vide reçue.', 'bot');
    } catch (err) {
        showError('Impossible de contacter le service. Vérifiez votre connexion.');
        console.error(err);
    } finally {
        setLoading(false);
        setInputEnabled(true);
        userInput.focus();
    }
}

// ── DOM helpers ────────────────────────────────────────────────────────────

function addMessage(text, role) {
    const row = document.createElement('div');
    row.className = `message-row ${role === 'user' ? 'user-row' : 'bot-row'}`;

    if (role === 'bot') {
        const avatar = document.createElement('div');
        avatar.className = 'avatar-small';
        avatar.innerHTML = '<i data-lucide="activity"></i>';
        row.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = `bubble ${role === 'user' ? 'user-bubble' : 'bot-bubble'}`;
    bubble.innerHTML = role === 'bot' ? renderMarkdown(text) : '';
    if (role === 'user') bubble.textContent = text;

    const time = document.createElement('div');
    time.className = 'time-stamp';
    time.textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    bubble.appendChild(time);

    row.appendChild(bubble);

    if (role === 'user') {
        const avatar = document.createElement('div');
        avatar.className = 'avatar-small';
        avatar.innerHTML = '<i data-lucide="user"></i>';
        row.appendChild(avatar);
    }

    messagesContainer.appendChild(row);
    lucide.createIcons();
    scrollToBottom();
}

function showError(text) {
    const div = document.createElement('div');
    div.className = 'message-error';
    div.textContent = text;
    messagesContainer.appendChild(div);
    scrollToBottom();
}

function setLoading(isLoading) {
    typingIndicator.style.display = isLoading ? 'flex' : 'none';
    if (isLoading) scrollToBottom();
}

function setInputEnabled(enabled) {
    userInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ── Markdown renderer ──────────────────────────────────────────────────────

function renderMarkdown(text) {
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    html = html.replace(/^### (.+)$/gm, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^## (.+)$/gm,  '<h2 class="md-h2">$1</h2>');
    html = html.replace(/^# (.+)$/gm,   '<h1 class="md-h1">$1</h1>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g,     '<em>$1</em>');

    html = html.replace(/((?:^- .+\n?)+)/gm, (block) => {
        const items = block.trim().split('\n')
            .map(line => `<li>${line.replace(/^- /, '')}</li>`)
            .join('');
        return `<ul class="md-ul">${items}</ul>`;
    });

    html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="md-blockquote">$1</blockquote>');

    html = html.split(/\n{2,}/).map(block => {
        block = block.trim();
        if (!block) return '';
        if (/^<(h[123]|ul|blockquote)/.test(block)) return block;
        return `<p class="md-p">${block.replace(/\n/g, '<br>')}</p>`;
    }).join('');

    return html;
}

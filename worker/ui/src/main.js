// ui/src/main.js

const { invoke } = window.__TAURI__.tauri;

// Estado global
let statusInterval = null;

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    startStatusPolling();
});

async function initializeApp() {
    addLog('🚀 Aplicação iniciada', 'info');
    await updateStatus();
    await loadConfig();
}

// ============================================================================
// EVENT LISTENERS & TABS
// ============================================================================

function setupEventListeners() {
    // --- LÓGICA DAS ABAS ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active de todos
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Ativa o clicado
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // --- BOTÕES DE AÇÃO ---
    document.getElementById('btn-start').addEventListener('click', handleStartWorker);
    document.getElementById('btn-stop').addEventListener('click', handleStopWorker);
    document.getElementById('btn-kill').addEventListener('click', handleKillExecution);
    document.getElementById('btn-refresh').addEventListener('click', async () => {
        addLog('🔄 Atualizando status...', 'info');
        await updateStatus();
    });

    // --- CONFIGURAÇÃO ---
    document.getElementById('config-form').addEventListener('submit', handleSaveConfig);

    document.getElementById('toggle-api-key').addEventListener('click', () => {
        const input = document.getElementById('api-key');
        const btn = document.getElementById('toggle-api-key');
        if (input.type === 'password') {
            input.type = 'text';
            btn.textContent = '🙈';
        } else {
            input.type = 'password';
            btn.textContent = '👁️';
        }
    });

    // --- LOGS ---
    document.getElementById('btn-clear-logs').addEventListener('click', clearLogs);
}

// ============================================================================
// FUNÇÕES DE API (Tauri Commands ou Fetch Local)
// ============================================================================
// Nota: Como estamos usando Vanilla JS + API Python local, usamos fetch direto
// para a porta 8765, mas poderíamos usar o Rust como proxy.

const API_URL = "http://127.0.0.1:8765";

async function updateStatus() {
    try {
        const response = await fetch(`${API_URL}/status`);
        if (!response.ok) throw new Error('Falha na conexão');

        const data = await response.json();
        renderStatus(data);
    } catch (error) {
        renderOffline();
        // Não logamos erro de conexão a cada segundo para não floodar
    }
}

function startStatusPolling() {
    // Atualiza a cada 2 segundos
    statusInterval = setInterval(updateStatus, 2000);
}

async function handleStartWorker() {
    try {
        addLog('⏳ Solicitando início...', 'info');
        const res = await fetch(`${API_URL}/start`, { method: 'POST' });
        const data = await res.json();
        addLog(`Resposta: ${JSON.stringify(data)}`, 'success');
        await updateStatus();
    } catch (e) {
        addLog(`Erro ao iniciar: ${e.message}`, 'error');
    }
}

async function handleStopWorker() {
    try {
        addLog('⏳ Parando serviço...', 'warning');
        const res = await fetch(`${API_URL}/stop`, { method: 'POST' });
        const data = await res.json();
        addLog(`Parado: ${JSON.stringify(data)}`, 'info');
        await updateStatus();
    } catch (e) {
        addLog(`Erro ao parar: ${e.message}`, 'error');
    }
}

async function handleKillExecution() {
    if (!confirm("Tem certeza que deseja matar o processo atual? Isso pode corromper dados.")) return;

    try {
        const res = await fetch(`${API_URL}/kill`, { method: 'POST' });
        const data = await res.json();
        addLog(`Processo Morto: ${JSON.stringify(data)}`, 'warning');
    } catch (e) {
        addLog(`Erro ao matar: ${e.message}`, 'error');
    }
}

async function handleSaveConfig(e) {
    e.preventDefault();

    const payload = {
        orchestrator_url: document.getElementById('orchestrator-url').value,
        api_key: document.getElementById('api-key').value,
        tenant_id: document.getElementById('tenant-id').value,
        worker_name: document.getElementById('worker-name').value
    };

    try {
        const res = await fetch(`${API_URL}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            addLog('✅ Configuração salva com sucesso!', 'success');
            alert("Configuração salva! O Worker reconectará automaticamente.");
        } else {
            throw new Error("Erro ao salvar");
        }
    } catch (e) {
        addLog(`Erro ao salvar config: ${e.message}`, 'error');
    }
}

async function loadConfig() {
    try {
        const response = await fetch(`${API_URL}/status`);
        const data = await response.json();

        if (data.config) {
            document.getElementById('orchestrator-url').value = data.config.orchestrator_url || '';
            // API Key geralmente não vem de volta por segurança, ou vem mascarada
            // document.getElementById('api-key').value = data.config.api_key || ''; 
            document.getElementById('tenant-id').value = data.config.tenant_id || '';
            document.getElementById('worker-name').value = data.worker_name || '';
        }
    } catch (e) {
        console.error("Erro ao carregar config inicial", e);
    }
}

// ============================================================================
// RENDERIZAÇÃO
// ============================================================================

function renderStatus(data) {
    // Indicador
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnKill = document.getElementById('btn-kill');

    // Reset classes
    indicator.className = 'indicator';

    if (data.running) {
        if (data.has_active_execution) {
            indicator.classList.add('busy');
            statusText.textContent = "EXECUTANDO";
            statusText.style.color = "var(--warning)";
            btnKill.disabled = false;
        } else {
            indicator.classList.add('online');
            statusText.textContent = "ONLINE (Aguardando)";
            statusText.style.color = "var(--success)";
            btnKill.disabled = true;
        }
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        indicator.classList.add('offline');
        statusText.textContent = "PARADO";
        statusText.style.color = "var(--danger)";
        btnStart.disabled = false;
        btnStop.disabled = true;
        btnKill.disabled = true;
    }

    // Dados
    document.getElementById('last-heartbeat').textContent = data.last_heartbeat ? new Date(data.last_heartbeat).toLocaleTimeString() : '-';
    document.getElementById('active-execution').textContent = data.current_execution_id || 'Nenhuma';
    document.getElementById('display-worker-name').textContent = data.worker_name;

    // Stats
    document.getElementById('stats-completed').textContent = data.stats.executions_completed;
    document.getElementById('stats-failed').textContent = data.stats.executions_failed;
}

function renderOffline() {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');

    indicator.className = 'indicator offline';
    statusText.textContent = "DESCONECTADO (Serviço Local Off)";
    statusText.style.color = "var(--text-muted)";

    document.getElementById('btn-start').disabled = true;
    document.getElementById('btn-stop').disabled = true;
}

// ============================================================================
// LOGS
// ============================================================================

function addLog(message, type = 'info') {
    const logOutput = document.getElementById('log-output');
    const timestamp = new Date().toLocaleTimeString('pt-BR');

    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] ${message}`;

    logOutput.insertBefore(logEntry, logOutput.firstChild);

    // Mantém no máximo 200 logs na memória da UI
    while (logOutput.children.length > 200) {
        logOutput.removeChild(logOutput.lastChild);
    }
}

function clearLogs() {
    document.getElementById('log-output').innerHTML = '';
    addLog('🗑️ Logs limpos', 'info');
}
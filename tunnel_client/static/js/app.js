let statusInterval = null;
let serverConfigured = false;
let editingTunnelId = null;
let currentView = 'table';
let sortDirection = 'asc';
let serverDomain = null;

// Initialize
init();

async function init() {
    // Check if server URL is pre-configured
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        serverConfigured = config.server_configured;

        if (serverConfigured) {
            // Hide server URL field if pre-configured
            const serverUrlGroup = document.getElementById('serverUrlGroup');
            if (serverUrlGroup) {
                serverUrlGroup.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Failed to load config:', e);
    }

    checkAuth();
}

async function checkAuth() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();

        if (data.authenticated) {
            // Extract domain from server URL (e.g., http://tunnel.ersantana.com:8000 -> tunnel.ersantana.com)
            if (data.server_url) {
                try {
                    const url = new URL(data.server_url);
                    serverDomain = url.hostname;
                } catch (e) {
                    serverDomain = null;
                }
            }
            showDashboard(data.email);
        } else {
            showLogin();
        }
    } catch (e) {
        console.error('Auth check failed:', e);
        showLogin();
    }
}

function showLogin() {
    document.getElementById('loginScreen').style.display = 'block';
    document.getElementById('dashboard').style.display = 'none';
    if (statusInterval) clearInterval(statusInterval);
}

function showDashboard(email) {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('userEmail').textContent = email;
    loadStatus();
    loadTunnels();
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(() => {
        loadStatus();
        loadTunnels();
    }, 5000);
}

async function handleLogin(e) {
    e.preventDefault();
    const serverUrlInput = document.getElementById('serverUrl');
    const serverUrl = serverConfigured ? null : serverUrlInput.value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    const payload = {email, password};
    if (serverUrl) {
        payload.server_url = serverUrl;
    }

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showDashboard(email);
        } else {
            const error = await res.json();
            showLoginAlert(error.detail || 'Login failed', 'error');
        }
    } catch (e) {
        showLoginAlert('Network error', 'error');
    }
}

async function handleLogout() {
    try {
        await fetch('/api/logout', {method: 'POST'});
    } catch (e) {}
    showLogin();
}

function showLoginAlert(message, type) {
    const container = document.getElementById('loginAlert');
    container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => container.innerHTML = '', 3000);
}

async function loadStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();

        const dot = document.getElementById('statusDot');
        const text = document.getElementById('statusText');
        const btnStart = document.getElementById('btnStart');
        const btnStop = document.getElementById('btnStop');
        const btnRestart = document.getElementById('btnRestart');

        if (data.running) {
            dot.classList.add('running');
            text.textContent = 'Connected (PID: ' + data.pid + ')';
            btnStart.style.display = 'none';
            btnStop.style.display = 'inline-block';
            btnRestart.style.display = 'inline-block';
        } else {
            dot.classList.remove('running');
            text.textContent = 'Disconnected';
            btnStart.style.display = 'inline-block';
            btnStop.style.display = 'none';
            btnRestart.style.display = 'none';
        }
    } catch (e) {
        console.error('Failed to load status:', e);
    }
}

async function loadTunnels() {
    try {
        const res = await fetch('/api/tunnels');
        if (res.status === 401) {
            showLogin();
            return;
        }
        if (!res.ok) {
            showAlert('Failed to load tunnels', 'error');
            return;
        }
        const data = await res.json();
        const list = document.getElementById('tunnelList');
        const countEl = document.getElementById('tunnelCount');

        let tunnels = data.tunnels || [];
        countEl.textContent = '(' + tunnels.length + ')';

        if (tunnels.length === 0) {
            list.innerHTML = '<div class="empty-state">No tunnels yet. Click "+ New Tunnel" to create one.</div>';
            return;
        }

        // Sort tunnels
        const sortBy = document.getElementById('sortBy').value;
        tunnels = sortTunnels(tunnels, sortBy, sortDirection);

        // Render based on current view
        if (currentView === 'table') {
            renderTableView(list, tunnels);
        } else {
            renderCardView(list, tunnels);
        }
    } catch (e) {
        console.error('Failed to load tunnels:', e);
        showAlert('Network error loading tunnels', 'error');
    }
}

function getPublicUrl(tunnel) {
    // Construct correct public URL using server domain
    if (tunnel.subdomain && serverDomain) {
        const protocol = tunnel.type === 'https' ? 'https' : 'http';
        return `${protocol}://${tunnel.subdomain}.${serverDomain}`;
    }
    return tunnel.public_url || null;
}

function sortTunnels(tunnels, sortBy, direction) {
    return tunnels.slice().sort((a, b) => {
        let aVal = a[sortBy];
        let bVal = b[sortBy];

        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        let result = 0;
        if (aVal < bVal) result = -1;
        else if (aVal > bVal) result = 1;

        return direction === 'asc' ? result : -result;
    });
}

function renderTableView(container, tunnels) {
    let html = `
        <table class="tunnel-table">
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Local</th>
                    <th>Remote</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    tunnels.forEach(t => {
        const isActive = t.is_active;
        const statusClass = isActive ? 'active' : '';

        let remoteText = '';
        const publicUrl = getPublicUrl(t);
        if (publicUrl) {
            remoteText = `<a href="${publicUrl}" target="_blank">${publicUrl}</a>`;
        } else if (t.remote_port) {
            remoteText = '[server]:' + t.remote_port;
        }

        html += `
            <tr>
                <td><div class="tunnel-status-dot ${statusClass}"></div></td>
                <td class="tunnel-name">${t.name}</td>
                <td><span class="tunnel-type">${t.type}</span></td>
                <td>${t.local_host}:${t.local_port}</td>
                <td class="tunnel-remote">${remoteText}</td>
                <td class="actions">
                    <button class="btn btn-secondary btn-sm" onclick='editTunnel(${JSON.stringify(t)})'>Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteTunnel(${t.id})">Delete</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderCardView(container, tunnels) {
    container.innerHTML = '';

    tunnels.forEach(t => {
        const item = document.createElement('div');
        item.className = 'tunnel-item';

        const isActive = t.is_active;
        const statusClass = isActive ? 'active' : '';

        let detailText = t.local_host + ':' + t.local_port;
        let urlHtml = '';

        const publicUrl = getPublicUrl(t);
        if (publicUrl) {
            urlHtml = `<div class="tunnel-url"><a href="${publicUrl}" target="_blank">${publicUrl}</a></div>`;
        } else if (t.remote_port) {
            detailText += ' → [server]:' + t.remote_port;
        }

        let lastConnected = '';
        if (t.last_connected) {
            lastConnected = 'Last connected: ' + new Date(t.last_connected).toLocaleString();
        }

        item.innerHTML = `
            <div class="tunnel-header">
                <div class="tunnel-name-wrap">
                    <div class="tunnel-status-dot ${statusClass}"></div>
                    <span class="tunnel-name">${t.name}</span>
                    <span class="tunnel-type">${t.type}</span>
                </div>
                <div>
                    <button class="btn btn-secondary btn-sm" onclick='editTunnel(${JSON.stringify(t)})'>Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteTunnel(${t.id})">Delete</button>
                </div>
            </div>
            <div class="tunnel-details">${detailText}</div>
            ${urlHtml}
            <div class="tunnel-meta">
                <span class="tunnel-last-connected">${lastConnected}</span>
                <span style="color: ${isActive ? '#22c55e' : '#64748b'}; font-size: 12px;">
                    ${isActive ? 'Active' : 'Inactive'}
                </span>
            </div>
        `;

        container.appendChild(item);
    });
}

function setView(view) {
    currentView = view;
    document.getElementById('btnTableView').classList.toggle('active', view === 'table');
    document.getElementById('btnCardView').classList.toggle('active', view === 'cards');
    loadTunnels();
}

function toggleSortDirection() {
    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    document.getElementById('sortDirBtn').textContent = sortDirection === 'asc' ? '↑' : '↓';
    loadTunnels();
}

function toggleCreateForm() {
    const form = document.getElementById('createForm');
    form.classList.toggle('show');
    if (!form.classList.contains('show')) {
        // Reset form when closing
        editingTunnelId = null;
        document.getElementById('formTitle').textContent = 'Create Tunnel';
        document.getElementById('formSubmitBtn').textContent = 'Create Tunnel';
        document.getElementById('tunnelName').value = '';
        document.getElementById('tunnelLocalPort').value = '';
        document.getElementById('tunnelLocalHost').value = '127.0.0.1';
        document.getElementById('tunnelSubdomain').value = '';
        document.getElementById('tunnelRemotePort').value = '';
    }
}

function editTunnel(tunnel) {
    editingTunnelId = tunnel.id;
    document.getElementById('formTitle').textContent = 'Edit Tunnel';
    document.getElementById('formSubmitBtn').textContent = 'Update Tunnel';
    document.getElementById('tunnelName').value = tunnel.name;
    document.getElementById('tunnelType').value = tunnel.type;
    document.getElementById('tunnelLocalPort').value = tunnel.local_port;
    document.getElementById('tunnelLocalHost').value = tunnel.local_host || '127.0.0.1';
    document.getElementById('tunnelSubdomain').value = tunnel.subdomain || '';
    document.getElementById('tunnelRemotePort').value = tunnel.remote_port || '';
    updateFormFields();
    document.getElementById('createForm').classList.add('show');
}

function updateFormFields() {
    const type = document.getElementById('tunnelType').value;
    const subdomainGroup = document.getElementById('subdomainGroup');
    const remotePortGroup = document.getElementById('remotePortGroup');

    if (type === 'tcp') {
        subdomainGroup.style.display = 'none';
        remotePortGroup.style.display = 'block';
    } else {
        subdomainGroup.style.display = 'block';
        remotePortGroup.style.display = 'none';
    }
}

async function createTunnel() {
    const name = document.getElementById('tunnelName').value.trim();
    const type = document.getElementById('tunnelType').value;
    const localPort = parseInt(document.getElementById('tunnelLocalPort').value);
    const localHost = document.getElementById('tunnelLocalHost').value.trim() || '127.0.0.1';
    const subdomain = document.getElementById('tunnelSubdomain').value.trim();
    const remotePort = parseInt(document.getElementById('tunnelRemotePort').value);

    if (!name || !localPort) {
        showAlert('Name and local port are required', 'error');
        return;
    }

    const payload = {name, type, local_port: localPort, local_host: localHost};
    if (type === 'tcp') {
        if (!remotePort) {
            showAlert('Remote port is required for TCP tunnels', 'error');
            return;
        }
        payload.remote_port = remotePort;
    } else {
        if (!subdomain) {
            showAlert('Subdomain is required for HTTP/HTTPS tunnels', 'error');
            return;
        }
        payload.subdomain = subdomain;
    }

    try {
        const method = editingTunnelId ? 'PUT' : 'POST';
        const url = editingTunnelId ? '/api/tunnels/' + editingTunnelId : '/api/tunnels';

        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (res.status === 401) {
            showLogin();
            return;
        }

        if (res.ok) {
            showAlert(editingTunnelId ? 'Tunnel updated successfully' : 'Tunnel created successfully', 'success');
            toggleCreateForm();
            loadTunnels();
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to save tunnel', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

async function deleteTunnel(id) {
    if (!confirm('Are you sure you want to delete this tunnel?')) return;

    try {
        const res = await fetch('/api/tunnels/' + id, {method: 'DELETE'});

        if (res.status === 401) {
            showLogin();
            return;
        }

        if (res.ok) {
            showAlert('Tunnel deleted', 'success');
            loadTunnels();
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to delete tunnel', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

async function startService() {
    try {
        const res = await fetch('/api/start', {method: 'POST'});
        if (res.ok) {
            showAlert('Service started', 'success');
            loadStatus();
            setTimeout(loadTunnels, 1000);
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to start service', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

async function stopService() {
    try {
        const res = await fetch('/api/stop', {method: 'POST'});
        if (res.ok) {
            showAlert('Service stopped', 'success');
            loadStatus();
            setTimeout(loadTunnels, 1000);
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to stop service', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

async function restartService() {
    try {
        const res = await fetch('/api/restart', {method: 'POST'});
        if (res.ok) {
            showAlert('Service restarted', 'success');
            loadStatus();
            setTimeout(loadTunnels, 1000);
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to restart service', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alert');
    alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => alertContainer.innerHTML = '', 3000);
}

async function exportTunnels() {
    try {
        const res = await fetch('/api/tunnels/export');
        if (res.status === 401) {
            showLogin();
            return;
        }
        if (!res.ok) {
            const error = await res.json();
            showAlert(error.detail || 'Failed to export tunnels', 'error');
            return;
        }
        const data = await res.json();

        // Download as JSON file
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tunnels-export.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showAlert('Tunnels exported successfully', 'success');
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

function triggerImport() {
    document.getElementById('importFileInput').click();
}

async function handleImportFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (!data.tunnels || !Array.isArray(data.tunnels)) {
            showAlert('Invalid file format: expected {"tunnels": [...]}', 'error');
            return;
        }

        const res = await fetch('/api/tunnels/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (res.status === 401) {
            showLogin();
            return;
        }

        const result = await res.json();

        if (result.created.length > 0) {
            showAlert(`Imported ${result.created.length} tunnel(s)`, 'success');
            loadTunnels();
        }
        if (result.failed && result.failed.length > 0) {
            const failedNames = result.failed.map(f => f.name).join(', ');
            showAlert(`Failed to import: ${failedNames}`, 'error');
        }
        if (result.created.length === 0 && (!result.failed || result.failed.length === 0)) {
            showAlert('No tunnels to import', 'error');
        }
    } catch (e) {
        if (e instanceof SyntaxError) {
            showAlert('Invalid JSON file', 'error');
        } else {
            showAlert('Failed to import tunnels', 'error');
        }
    }

    // Reset file input
    event.target.value = '';
}

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
        if (t.type === 'ssh' && t.ssh_connection_string) {
            remoteText = `<span class="ssh-connection" onclick="copyToClipboard('${t.ssh_connection_string}')" title="Click to copy">${t.ssh_connection_string}</span>`;
        } else if (publicUrl) {
            remoteText = `<a href="${publicUrl}" target="_blank">${publicUrl}</a>`;
        } else if (t.remote_port) {
            remoteText = '[server]:' + t.remote_port;
        }

        let actionsHtml = `
            <button class="btn btn-secondary btn-sm" onclick='editTunnel(${JSON.stringify(t)})'>Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteTunnel(${t.id})">Delete</button>
        `;
        if (t.type === 'ssh') {
            actionsHtml = `<button class="btn btn-sm" style="background:#a78bfa;color:white" onclick="testSSH(${t.id})">Test</button> ` + actionsHtml;
        }

        html += `
            <tr>
                <td><div class="tunnel-status-dot ${statusClass}"></div></td>
                <td class="tunnel-name">${t.name}</td>
                <td><span class="tunnel-type">${t.type}</span></td>
                <td>${t.local_host}:${t.local_port}</td>
                <td class="tunnel-remote">${remoteText}</td>
                <td class="actions">${actionsHtml}</td>
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

        if (t.type === 'ssh' && t.ssh_connection_string) {
            urlHtml = `<div class="tunnel-url"><span class="ssh-connection" onclick="copyToClipboard('${t.ssh_connection_string}')" title="Click to copy">${t.ssh_connection_string}</span></div>`;
        } else {
            const publicUrl = getPublicUrl(t);
            if (publicUrl) {
                urlHtml = `<div class="tunnel-url"><a href="${publicUrl}" target="_blank">${publicUrl}</a></div>`;
            } else if (t.remote_port) {
                detailText += ' → [server]:' + t.remote_port;
            }
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
        document.getElementById('tunnelSSHUser').value = '';
        document.getElementById('sshUserRow').style.display = 'none';
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
    document.getElementById('tunnelSSHUser').value = tunnel.ssh_user || '';
    updateFormFields();
    document.getElementById('createForm').classList.add('show');
}

function updateFormFields() {
    const type = document.getElementById('tunnelType').value;
    const subdomainGroup = document.getElementById('subdomainGroup');
    const remotePortGroup = document.getElementById('remotePortGroup');
    const sshUserRow = document.getElementById('sshUserRow');

    if (type === 'tcp') {
        subdomainGroup.style.display = 'none';
        remotePortGroup.style.display = 'block';
        sshUserRow.style.display = 'none';
    } else if (type === 'ssh') {
        subdomainGroup.style.display = 'none';
        remotePortGroup.style.display = 'block';
        sshUserRow.style.display = 'grid';
        // Set SSH defaults if creating new
        if (!editingTunnelId) {
            if (!document.getElementById('tunnelLocalPort').value) {
                document.getElementById('tunnelLocalPort').value = '22';
            }
            if (document.getElementById('tunnelLocalHost').value === '127.0.0.1') {
                document.getElementById('tunnelLocalHost').value = 'host.docker.internal';
            }
        }
    } else {
        subdomainGroup.style.display = 'block';
        remotePortGroup.style.display = 'none';
        sshUserRow.style.display = 'none';
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

    const sshUser = document.getElementById('tunnelSSHUser').value.trim();

    const payload = {name, type, local_port: localPort, local_host: localHost};
    if (type === 'ssh') {
        if (!remotePort) {
            showAlert('Remote port is required for SSH tunnels', 'error');
            return;
        }
        if (!sshUser) {
            showAlert('SSH user is required for SSH tunnels', 'error');
            return;
        }
        payload.remote_port = remotePort;
        payload.ssh_user = sshUser;
    } else if (type === 'tcp') {
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

// ==================== SSH FUNCTIONS ====================

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showAlert('Copied to clipboard', 'success');
    });
}

async function testSSH(tunnelId) {
    showAlert('Testing SSH connection...', 'success');
    try {
        const res = await fetch(`/api/tunnels/${tunnelId}/test-ssh`);
        if (!res.ok) {
            const error = await res.json();
            showAlert(error.detail || 'Test failed', 'error');
            return;
        }
        const data = await res.json();
        if (data.is_ssh) {
            showAlert(`SSH is reachable! Banner: ${data.ssh_banner}`, 'success');
        } else if (data.reachable) {
            showAlert('Port is reachable but no SSH banner detected', 'error');
        } else {
            showAlert('SSH is not reachable - check that sshd is running and the tunnel is active', 'error');
        }
    } catch (e) {
        showAlert('Failed to test SSH connection', 'error');
    }
}

async function loadSSHKeys() {
    try {
        const res = await fetch('/api/ssh-keys');
        if (res.status === 401) {
            showLogin();
            return;
        }
        if (!res.ok) return;

        const data = await res.json();
        const keys = data.keys || [];
        const container = document.getElementById('sshKeyList');
        const countEl = document.getElementById('sshKeyCount');

        countEl.textContent = '(' + keys.length + ')';

        if (keys.length === 0) {
            container.innerHTML = '<div class="empty-state">No SSH keys yet. Click "+ Add Key" to add one.</div>';
            return;
        }

        container.innerHTML = keys.map(k => `
            <div class="ssh-key-item">
                <div class="ssh-key-header">
                    <div>
                        <span class="ssh-key-name">${k.name}</span>
                        <span class="ssh-key-fingerprint">${k.fingerprint}</span>
                    </div>
                    <button class="btn btn-danger btn-sm" onclick="deleteSSHKey(${k.id}, '${k.name}')">Delete</button>
                </div>
                <div class="ssh-key-value">${k.public_key.substring(0, 80)}...</div>
                <div class="ssh-key-meta">Added ${new Date(k.created_at).toLocaleString()}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load SSH keys:', e);
    }
}

function toggleAddKeyForm() {
    const form = document.getElementById('addKeyForm');
    form.classList.toggle('show');
    if (!form.classList.contains('show')) {
        document.getElementById('sshKeyName').value = '';
        document.getElementById('sshKeyPublicKey').value = '';
    }
}

async function addSSHKey() {
    const name = document.getElementById('sshKeyName').value.trim();
    const publicKey = document.getElementById('sshKeyPublicKey').value.trim();

    if (!name || !publicKey) {
        showAlert('Name and public key are required', 'error');
        return;
    }

    try {
        const res = await fetch('/api/ssh-keys', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, public_key: publicKey})
        });

        if (res.ok) {
            showAlert('SSH key added successfully', 'success');
            toggleAddKeyForm();
            loadSSHKeys();
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to add SSH key', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

async function deleteSSHKey(keyId, keyName) {
    if (!confirm(`Delete SSH key "${keyName}"?`)) return;

    try {
        const res = await fetch(`/api/ssh-keys/${keyId}`, {method: 'DELETE'});
        if (res.ok) {
            showAlert('SSH key deleted', 'success');
            loadSSHKeys();
        } else {
            const error = await res.json();
            showAlert(error.detail || 'Failed to delete SSH key', 'error');
        }
    } catch (e) {
        showAlert('Network error', 'error');
    }
}

function renderSSHDInstructions() {
    const container = document.getElementById('sshdInstructions');
    container.innerHTML = `
        <p style="color:#94a3b8;margin-bottom:15px">Follow these steps to set up an SSH server in WSL2 so you can connect through the tunnel.</p>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">1. Install OpenSSH Server</h3>
        <div class="code-block">sudo apt update && sudo apt install openssh-server</div>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">2. Configure sshd</h3>
        <div class="code-block">sudo sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config</div>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">3. Set Up authorized_keys</h3>
        <p style="color:#94a3b8;font-size:13px;margin-bottom:8px">Add your public keys (from the SSH Keys tab above) to the authorized_keys file:</p>
        <div class="code-block">mkdir -p ~/.ssh && chmod 700 ~/.ssh
# Paste your public key(s) into this file:
nano ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys</div>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">4. Start sshd</h3>
        <div class="code-block">sudo service ssh start</div>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">5. WSL2 Notes</h3>
        <ul style="color:#94a3b8;font-size:13px;padding-left:20px;line-height:1.8">
            <li>WSL2 does not start sshd automatically. Run <code style="color:#a78bfa">sudo service ssh start</code> after each reboot.</li>
            <li>To auto-start sshd, add the command to your <code style="color:#a78bfa">~/.bashrc</code> or use a Windows Task Scheduler task.</li>
            <li>The tunnel uses <code style="color:#a78bfa">host.docker.internal</code> as local_host to reach WSL2 from the Docker container.</li>
            <li>Make sure port 22 is not blocked by Windows Firewall.</li>
        </ul>

        <h3 style="color:#38bdf8;font-size:14px;margin:15px 0 8px">6. Test Locally</h3>
        <div class="code-block"># From WSL2 itself:
ssh localhost
# From Windows (PowerShell):
ssh username@localhost</div>
    `;
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
        const yamlText = await res.text();

        // Download as YAML file
        const blob = new Blob([yamlText], {type: 'application/x-yaml'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tunnels.yaml';
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
        const yamlText = await file.text();

        const res = await fetch('/api/tunnels/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-yaml'},
            body: yamlText
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
        showAlert('Failed to import tunnels', 'error');
    }

    // Reset file input
    event.target.value = '';
}

// ==================== METRICS TAB ====================

let responseTimeChart = null;
let requestsChart = null;
let metricsInterval = null;
let currentTab = 'tunnels';

function showTab(tab) {
    currentTab = tab;

    // Update tab buttons
    document.getElementById('tabTunnels').classList.toggle('active', tab === 'tunnels');
    document.getElementById('tabSshkeys').classList.toggle('active', tab === 'sshkeys');
    document.getElementById('tabMetrics').classList.toggle('active', tab === 'metrics');

    // Update tab content
    const tunnelsTab = document.getElementById('tunnelsTab');
    const sshkeysTab = document.getElementById('sshkeysTab');
    const metricsTab = document.getElementById('metricsTab');

    tunnelsTab.style.display = 'none';
    tunnelsTab.classList.remove('active');
    sshkeysTab.style.display = 'none';
    sshkeysTab.classList.remove('active');
    metricsTab.style.display = 'none';
    metricsTab.classList.remove('active');

    if (tab === 'tunnels') {
        tunnelsTab.style.display = 'block';
        tunnelsTab.classList.add('active');
    } else if (tab === 'sshkeys') {
        sshkeysTab.style.display = 'block';
        sshkeysTab.classList.add('active');
        loadSSHKeys();
        renderSSHDInstructions();
    } else if (tab === 'metrics') {
        metricsTab.style.display = 'block';
        metricsTab.classList.add('active');
        initMetrics();
        loadMetrics();
    }
}

function initMetrics() {
    // Initialize charts if not already done
    if (responseTimeChart) return;

    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#94a3b8' }
            }
        },
        scales: {
            x: {
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' }
            },
            y: {
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                beginAtZero: true
            }
        }
    };

    // Response time histogram
    const rtCtx = document.getElementById('responseTimeChart');
    if (rtCtx) {
        responseTimeChart = new Chart(rtCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['<100ms', '100-300ms', '300-500ms', '500-1000ms', '>1000ms'],
                datasets: [{
                    label: 'Requests',
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: ['#22c55e', '#38bdf8', '#f59e0b', '#ef4444', '#dc2626'],
                    borderWidth: 0
                }]
            },
            options: chartDefaults
        });
    }

    // Requests over time
    const reqCtx = document.getElementById('requestsChart');
    if (reqCtx) {
        requestsChart = new Chart(reqCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Requests',
                    data: [],
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                ...chartDefaults,
                elements: {
                    point: { radius: 2 }
                }
            }
        });
    }

    // Populate tunnel dropdown
    populateTunnelDropdown();
}

async function populateTunnelDropdown() {
    try {
        const res = await fetch('/api/tunnels');
        if (!res.ok) return;
        const data = await res.json();
        const tunnels = data.tunnels || [];

        const select = document.getElementById('metricsTunnel');
        select.innerHTML = '<option value="">All Tunnels</option>';
        tunnels.forEach(t => {
            const option = document.createElement('option');
            option.value = t.name;
            option.textContent = t.name;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load tunnels for dropdown:', e);
    }
}

async function loadMetrics() {
    const period = document.getElementById('metricsPeriod').value;
    const tunnelName = document.getElementById('metricsTunnel').value || null;

    try {
        // Fetch summary and slow requests in parallel
        const [summaryRes, metricsRes] = await Promise.all([
            fetch(`/api/metrics/summary?period=${period}${tunnelName ? '&tunnel_name=' + tunnelName : ''}`),
            fetch(`/api/metrics?min_response_time=500&limit=20${tunnelName ? '&tunnel_name=' + tunnelName : ''}`)
        ]);

        if (summaryRes.status === 503 || metricsRes.status === 503) {
            // Server metrics not available
            document.getElementById('metricsNotConfigured').style.display = 'block';
            document.getElementById('metricsContent').style.display = 'none';
            return;
        }

        document.getElementById('metricsNotConfigured').style.display = 'none';
        document.getElementById('metricsContent').style.display = 'block';

        if (summaryRes.ok) {
            const summary = await summaryRes.json();
            updateSummaryCards(summary);
            updateCharts(summary);
        }

        if (metricsRes.ok) {
            const metrics = await metricsRes.json();
            updateSlowRequestsTable(metrics.metrics || []);
        }
    } catch (e) {
        console.error('Failed to load metrics:', e);
        // Show placeholder values
        document.getElementById('totalRequests').textContent = '--';
        document.getElementById('avgResponseTime').textContent = '--';
        document.getElementById('p95ResponseTime').textContent = '--';
        document.getElementById('totalTraffic').textContent = '--';
    }
}

function updateSummaryCards(summary) {
    document.getElementById('totalRequests').textContent = formatNumber(summary.total_requests || 0);
    document.getElementById('avgResponseTime').textContent = formatDuration(summary.avg_response_time_ms || 0);
    document.getElementById('p95ResponseTime').textContent = formatDuration(summary.p95_response_time_ms || 0);

    const trafficIn = summary.total_bytes_in || 0;
    const trafficOut = summary.total_bytes_out || 0;
    document.getElementById('totalTraffic').textContent = `${formatBytes(trafficIn)} / ${formatBytes(trafficOut)}`;
}

function updateCharts(summary) {
    // Update response time histogram from status_codes data
    // This is a placeholder - real data would come from response time buckets
    if (responseTimeChart && summary.status_codes) {
        const total = summary.total_requests || 1;
        const fast = Math.floor(total * 0.6);
        const medium = Math.floor(total * 0.25);
        const slow = Math.floor(total * 0.1);
        const verySlow = Math.floor(total * 0.04);
        const critical = total - fast - medium - slow - verySlow;

        responseTimeChart.data.datasets[0].data = [fast, medium, slow, verySlow, critical];
        responseTimeChart.update();
    }

    // For requests over time, we'd need time-series data from the server
    // For now, just show placeholder
    if (requestsChart) {
        const rpm = summary.requests_per_minute || 0;
        // Generate fake time labels for demo
        const labels = [];
        const data = [];
        const now = new Date();
        for (let i = 11; i >= 0; i--) {
            const t = new Date(now - i * 5 * 60000);
            labels.push(t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            data.push(Math.floor(rpm * 5 * (0.8 + Math.random() * 0.4)));
        }
        requestsChart.data.labels = labels;
        requestsChart.data.datasets[0].data = data;
        requestsChart.update();
    }
}

function updateSlowRequestsTable(metrics) {
    const tbody = document.getElementById('slowRequestsBody');

    if (!metrics || metrics.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:#64748b;text-align:center">No slow requests found</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    metrics.forEach(m => {
        const row = document.createElement('tr');
        const statusClass = getStatusClass(m.status_code);
        const timeClass = getTimeClass(m.response_time_ms);
        const when = new Date(m.timestamp).toLocaleString();

        row.innerHTML = `
            <td>${m.tunnel_name}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${m.request_path}</td>
            <td>${m.request_method}</td>
            <td class="${statusClass}">${m.status_code}</td>
            <td class="${timeClass}">${m.response_time_ms}ms</td>
            <td style="color:#64748b;font-size:12px">${when}</td>
        `;
        tbody.appendChild(row);
    });
}

function getStatusClass(code) {
    if (code >= 200 && code < 300) return 'status-2xx';
    if (code >= 300 && code < 400) return 'status-3xx';
    if (code >= 400 && code < 500) return 'status-4xx';
    return 'status-5xx';
}

function getTimeClass(ms) {
    if (ms < 500) return 'time-fast';
    if (ms < 1000) return 'time-medium';
    return 'time-slow';
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDuration(ms) {
    if (ms < 1000) return Math.round(ms) + 'ms';
    return (ms / 1000).toFixed(2) + 's';
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

# Tunnel Client

Web-based client for managing your tunnels with a clean interface.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](./docs/getting-started/) | Installation and first steps |
| [Configuration](./docs/configuration/) | YAML config file reference |
| [Usage](./docs/usage/) | Web UI, CLI, and service management |
| [API Reference](./docs/api/) | REST API endpoints |
| [Examples](./docs/examples/) | Common use cases and recipes |
| [Troubleshooting](./docs/troubleshooting/) | Common issues and solutions |
| [Architecture](./docs/architecture/) | How it works internally |

> Full documentation: [docs/README.md](./docs/)

---

## Features

- **YAML Configuration** - Define tunnels in `tunnels.yaml`
- **Web UI** - Monitor status at http://127.0.0.1:3000
- **Token Authentication** - Secure connection to server
- **Status Monitoring** - Real-time connection status
- **Service Control** - Start/stop/restart from UI
- **Hot Reload** - Reload config without restart

## Installation

### Requirements
- Python 3.8+
- pip3
- Tunnel server URL and token

### Quick Install

```bash
chmod +x install.sh
./install.sh
```

### Manual Install

```bash
# Install Python dependencies
pip3 install -r requirements.txt --break-system-packages

# Install frpc
FRP_VERSION="0.52.3"
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz
tar -xzf frp_*.tar.gz
sudo cp frp_*/frpc /usr/local/bin/
sudo chmod +x /usr/local/bin/frpc

# Create config directory
sudo mkdir -p /etc/frp
```

## Configuration

### Quick Start

1. Copy the example config:
   ```bash
   cp tunnels.example.yaml tunnels.yaml
   ```

2. Edit `tunnels.yaml` with your settings:
   ```yaml
   server:
     url: "your-server.com:7000"
     token: "your-token-here"

   tunnels:
     - name: my-api
       description: "My REST API"
       type: http
       local_port: 8080
       subdomain: api
   ```

3. Start the client:
   ```bash
   python3 app.py
   ```

4. Open browser: `http://127.0.0.1:3000`

### Config File Format

```yaml
# Server connection
server:
  url: "your-server.com:7000"    # Server address and port
  token: "your-token-here"        # Authentication token

# Tunnel definitions
tunnels:
  # HTTP tunnel - uses subdomain routing
  - name: my-webapp
    description: "My web application"
    type: http
    local_port: 8080
    subdomain: myapp
    # Access at: http://myapp.your-server.com

  # TCP tunnel - uses port mapping
  - name: postgres
    description: "PostgreSQL database"
    type: tcp
    local_port: 5432
    remote_port: 15432
    # Access at: your-server.com:15432
```

### Tunnel Types

| Type | Use Case | Required Field |
|------|----------|----------------|
| `http` | Web apps, APIs | `subdomain` |
| `https` | Secure web traffic | `subdomain` |
| `tcp` | Databases, SSH | `remote_port` |
| `udp` | Gaming, streaming | `remote_port` |

## Usage

### Web UI

Open `http://127.0.0.1:3000` to:
- View all configured tunnels
- Start/Stop/Restart the frpc service
- Reload configuration after editing `tunnels.yaml`

### CLI Options

```bash
python3 app.py                  # Default: localhost:3000
python3 app.py --port 3001      # Custom port
python3 app.py --host 0.0.0.0   # Listen on all interfaces
```

### Modifying Tunnels

1. Edit `tunnels.yaml`
2. Click "Reload Config" in the web UI (or restart the app)
3. Changes take effect immediately

## Running as Service

### Enable Auto-start

```bash
sudo systemctl enable tunnel-client
sudo systemctl start tunnel-client
```

### Service Management

```bash
systemctl status tunnel-client      # Check status
sudo systemctl start tunnel-client  # Start
sudo systemctl stop tunnel-client   # Stop
sudo systemctl restart tunnel-client # Restart
journalctl -u tunnel-client -f      # View logs
```

## Examples

### Example 1: Local API Development

```yaml
tunnels:
  - name: dev-api
    description: "Development API"
    type: http
    local_port: 8080
    subdomain: myapi
```

```bash
# Start your API locally
uvicorn main:app --port 8080

# Access from anywhere
curl https://myapi.yourdomain.com
```

### Example 2: React App Demo

```yaml
tunnels:
  - name: react-demo
    description: "React demo app"
    type: http
    local_port: 3000
    subdomain: demo
```

```bash
npm start  # Runs on :3000
# Share: https://demo.yourdomain.com
```

### Example 3: Database Access

```yaml
tunnels:
  - name: postgres
    description: "PostgreSQL database"
    type: tcp
    local_port: 5432
    remote_port: 15432
```

```bash
# Team connects remotely
psql -h your-server.com -p 15432 -U postgres
```

### Example 4: Multiple Services

```yaml
tunnels:
  - name: api
    type: http
    local_port: 8080
    subdomain: api

  - name: frontend
    type: http
    local_port: 3000
    subdomain: app

  - name: db
    type: tcp
    local_port: 5432
    remote_port: 15432
```

Access:
- `api.yourdomain.com`
- `app.yourdomain.com`
- `your-server.com:15432`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/config` | GET | Current configuration info |
| `/api/tunnels` | GET | List all tunnels |
| `/api/status` | GET | Service status (running/stopped) |
| `/api/start` | POST | Start frpc service |
| `/api/stop` | POST | Stop frpc service |
| `/api/restart` | POST | Restart frpc service |
| `/api/reload` | POST | Reload config from YAML |

## Troubleshooting

> Full troubleshooting guide: [docs/troubleshooting/](./docs/troubleshooting/)

### Quick Fixes

| Problem | Solution |
|---------|----------|
| Can't connect to server | Check URL format: `server.com:7000` (not `:8000`) |
| Service won't start | Run `which frpc` to verify installation |
| Tunnel not working | Check local service: `curl localhost:8080` |
| Port already in use | Use `--port 3001` or check `lsof -i :3000` |
| Config not loading | Run `python3 -c "import yaml; yaml.safe_load(open('tunnels.yaml'))"` |

### Logs

```bash
# Application logs (if running directly)
python3 app.py

# frpc logs
cat /tmp/frpc.log
tail -f /tmp/frpc.log  # Follow in real-time
```

## Security

### Config File Safety

Never commit `tunnels.yaml` to git. Add to `.gitignore`:
```
tunnels.yaml
```

### Local Access Only

The client UI runs on `127.0.0.1:3000` by default - only accessible from your machine.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Main application |
| `tunnels.yaml` | Your tunnel configuration |
| `tunnels.example.yaml` | Example config template |
| `/etc/frp/frpc.ini` | Generated frpc config |
| `/tmp/frpc.log` | frpc log file |
| `/tmp/frpc.pid` | frpc process ID |

## Updating

```bash
sudo systemctl stop tunnel-client
git pull
pip3 install -r requirements.txt --break-system-packages
sudo systemctl start tunnel-client
```

## Uninstall

```bash
sudo systemctl stop tunnel-client
sudo systemctl disable tunnel-client
sudo rm /etc/systemd/system/tunnel-client.service
sudo rm /usr/local/bin/frpc
sudo rm -rf /etc/frp
sudo systemctl daemon-reload
```

---

## See Also

### Documentation
- [Full Documentation](./docs/) - Complete documentation index
- [Getting Started](./docs/getting-started/) - Installation guide
- [Configuration Reference](./docs/configuration/) - All config options
- [API Reference](./docs/api/) - REST API documentation
- [Examples & Recipes](./docs/examples/) - Common use cases

### Files
- [tunnels.example.yaml](./tunnels.example.yaml) - Example configuration
- [CLAUDE.md](./CLAUDE.md) - AI assistant guide

### External
- [FRP Project](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework used

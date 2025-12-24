# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tunnel Client is a web-based UI for managing FRP (Fast Reverse Proxy) tunnels. It provides a FastAPI backend with an embedded HTML/CSS/JS frontend served from a single `app.py` file. Tunnels are defined in a YAML config file (`tunnels.yaml`), and the web UI provides read-only monitoring and service control.

## Commands

### Run the application
```bash
python3 app.py
```
Access at http://127.0.0.1:3000

### CLI options
```bash
python3 app.py --port 3001      # Use different port
python3 app.py --host 0.0.0.0   # Listen on all interfaces
python3 app.py --help           # Show all options
```

### Install dependencies
```bash
pip3 install -r requirements.txt --break-system-packages
```

### Full installation (includes frpc binary and systemd service)
```bash
./install.sh
```

### Service management
```bash
sudo systemctl start tunnel-client
sudo systemctl stop tunnel-client
sudo systemctl restart tunnel-client
journalctl -u tunnel-client -f  # View logs
```

## Architecture

### Configuration Flow
```
tunnels.yaml → app.py → /etc/frp/frpc.ini → frpc process
                 ↓
              Web UI (read-only monitoring)
```

### Single-File Application
The entire application is in `app.py`:
- **Lines 1-35**: Imports, logging setup, and configuration constants
- **Lines 39-76**: YAML config loading functions (`load_config`, `get_cached_config`, `reload_config`)
- **Lines 80-115**: FastAPI app lifespan (startup/shutdown with config loading)
- **Lines 119-145**: Pydantic Tunnel model for reference/validation
- **Lines 150-205**: API endpoints for config and tunnels (read from YAML)
- **Lines 206-330**: Service control endpoints (start/stop/restart with process group management)
- **Lines 333-405**: frpc config generation from YAML with file permission hardening
- **Lines 408-857**: Embedded HTML/CSS/JS UI in `get_client_html()`
- **Lines 860-870**: Main block with argparse CLI

### Configuration Files
- **`tunnels.yaml`**: User-defined tunnel configuration (server URL, token, tunnels)
- **`tunnels.example.yaml`**: Template with examples
- **`/etc/frp/frpc.ini`**: Auto-generated frpc config with 0600 permissions
- **`/tmp/frpc.log`**: frpc subprocess output for debugging
- **`/tmp/frpc.pid`**: frpc process ID with 0600 permissions

### YAML Config Format
```yaml
server:
  url: "server.com:7000"
  token: "your-token"

tunnels:
  - name: my-api
    description: "Optional description"
    type: http
    local_port: 8080
    subdomain: api

  - name: database
    type: tcp
    local_port: 5432
    remote_port: 15432
```

### Key API Endpoints
- `GET /api/config` - Get configuration status (configured, server_url, tunnel_count)
- `GET /api/tunnels` - List all tunnels from YAML config
- `POST /api/reload` - Reload config from YAML file
- `POST /api/start`, `POST /api/stop`, `POST /api/restart` - Control frpc process
- `GET /api/status` - Check if frpc is running

### Process Management
The app manages the `frpc` subprocess:
- PID stored in `/tmp/frpc.pid` with 0600 permissions
- Uses process group kill for clean shutdown
- Waits up to 5 seconds for graceful termination
- Config regenerated and service restarted when reload is triggered

### Input Validation
Tunnel model (for reference) validates:
- Name: alphanumeric with underscores/hyphens, 1-50 chars
- Type: http, https, tcp, or udp only
- Ports: 1-65535 range
- Subdomain: DNS-safe format, required for http/https
- Remote port: required for tcp/udp

## Dependencies
- FastAPI + Uvicorn for web server
- Pydantic for request validation with Field constraints
- PyYAML for config file parsing
- External: `frpc` binary at `/usr/local/bin/frpc`

## Files
| File | Purpose |
|------|---------|
| `app.py` | Main FastAPI application with embedded UI |
| `tunnels.yaml` | User's tunnel configuration |
| `tunnels.example.yaml` | Example config template |
| `requirements.txt` | Python dependencies |
| `install.sh` | Installation script for frpc and systemd |
| `README.md` | User documentation |

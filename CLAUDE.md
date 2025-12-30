# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tunnel Client is a web-based UI for managing FRP (Fast Reverse Proxy) tunnels. It provides a FastAPI backend that communicates with a tunnel server API and a web frontend for tunnel management. Users authenticate with their server credentials, and the client manages the frpc process locally.

## Commands

### Run the application
```bash
python -m tunnel_client.main
```
Access at http://127.0.0.1:3000

### CLI options
```bash
python -m tunnel_client.main --port 3001      # Use different port
python -m tunnel_client.main --host 0.0.0.0   # Listen on all interfaces
python -m tunnel_client.main --help           # Show all options
```

### Install dependencies
```bash
pip3 install -r requirements.txt --break-system-packages
```

### Docker Compose (recommended)
```bash
docker compose up -d              # Start both containers
docker compose logs -f            # View logs (both containers)
docker compose logs -f frpc       # View frpc logs only
docker compose down               # Stop
docker compose build --no-cache   # Rebuild tunnel-client
docker compose restart frpc       # Restart frpc after token change
```

### Service management
```bash
sudo systemctl start tunnel-client
sudo systemctl stop tunnel-client
sudo systemctl restart tunnel-client
journalctl -u tunnel-client -f  # View logs
```

## Architecture

### Docker Containers
```
┌─────────────────────┐    ┌─────────────────────┐
│   tunnel-client     │    │        frpc         │
│   (Web UI + API)    │    │   (Tunnel Proxy)    │
│                     │    │                     │
│  - FastAPI server   │    │  - frpc binary      │
│  - Config generator │───►│  - Admin API :7400  │
│  - Admin API client │    │  - Always running   │
└─────────────────────┘    └─────────────────────┘
         │                          │
         ▼                          ▼
   /etc/frp/frpc.toml         frps server
   (shared volume)
```

### Flow
```
User Login → Server API → access_token + tunnel_token
                ↓
tunnel_client → Server API → Tunnel CRUD
                ↓
          Generate frpc.toml → frpc container → frps server
                ↓
          HTTP reload → frpc admin API (:7400)
```

### Project Structure
```
tunnel_client/
├── __init__.py           # Package init with version
├── main.py               # FastAPI app entry point, lifespan
├── config.py             # Settings, constants, logging
├── models/
│   ├── __init__.py
│   └── schemas.py        # Pydantic request/response models
├── services/
│   ├── __init__.py
│   ├── credentials.py    # Credentials load/save/clear
│   ├── frpc.py           # frpc process management & config generation
│   └── api_client.py     # Server API client (tunnel CRUD)
├── routers/
│   ├── __init__.py
│   ├── auth.py           # /api/login, /api/logout, /api/auth/status
│   ├── tunnels.py        # /api/tunnels CRUD
│   └── service.py        # /api/start, /api/stop, /api/restart, /api/status
├── static/
│   ├── css/
│   │   └── style.css     # UI styles
│   └── js/
│       └── app.js        # Frontend JavaScript
└── templates/
    └── index.html        # Main HTML template
```

### Key Modules

- **config.py**: Configuration constants (file paths, logging setup)
- **services/credentials.py**: Manages credentials.json (server_url, access_token, tunnel_token, user_email)
- **services/api_client.py**: HTTP client for tunnel server API
- **services/frpc.py**: frpc config generation and admin API client (reload, status)
- **routers/auth.py**: Authentication endpoints (login saves credentials, auto-starts frpc)
- **routers/tunnels.py**: Tunnel CRUD (proxies to server API)
- **routers/service.py**: frpc service control

### Configuration Files
- **`credentials.json`**: User credentials (auto-created on login, 0600 permissions)
- **`/etc/frp/frpc.toml`**: Auto-generated frpc config (TOML format, shared volume)

### Key API Endpoints
- `GET /api/config` - Get client configuration (server_url if pre-configured)
- `POST /api/login` - Login to server, save credentials
- `POST /api/logout` - Stop frpc, clear credentials
- `GET /api/auth/status` - Check if authenticated
- `GET /api/tunnels` - List tunnels from server
- `POST /api/tunnels` - Create tunnel on server
- `PUT /api/tunnels/{id}` - Update tunnel on server
- `DELETE /api/tunnels/{id}` - Delete tunnel from server
- `GET /api/tunnels/export` - Export all tunnels as JSON
- `POST /api/tunnels/import` - Import tunnels from JSON
- `GET /api/status` - Check if frpc is running
- `POST /api/start`, `POST /api/stop`, `POST /api/restart` - Control frpc process

### Environment Variables
- `SERVER_URL` - Pre-configured server URL (hides server URL field in login form)
- `TUNNEL_TOKEN` - Override tunnel token from credentials (takes priority over credentials.json)
- `FRPC_ADMIN_URL` - frpc admin API URL (default: `http://frpc:7400`)

### Container Architecture
- **frpc container**: Always running, auto-restarts on failure (`restart: unless-stopped`)
- **tunnel-client container**: Generates config, calls frpc admin API to reload
- **Shared volume**: `/etc/frp` contains `frpc.toml` config
- **Hot reload**: Config changes applied via `http://frpc:7400/api/reload` (no container restart needed)

### Credentials Caching
- Credentials are cached in memory at startup (`services/credentials.py`)
- If `credentials.json` is updated externally, restart tunnel-client container
- The frpc config (`/etc/frp/frpc.toml`) is regenerated on login and tunnel changes

## Docker Networking

When running in Docker, `local_host: 127.0.0.1` refers to the frpc container itself, not the host or other containers.

### Tunneling to Other Containers
1. Connect the **frpc** container to the same Docker network as target services:
   ```bash
   docker network connect <network-name> frpc
   ```

2. Update tunnels to use container names as `local_host`:
   ```bash
   curl -X PUT http://localhost:3002/api/tunnels/1 \
     -H 'Content-Type: application/json' \
     -d '{"name":"myapp","type":"http","local_port":5000,"local_host":"my-container-name","subdomain":"myapp"}'
   ```

3. Reload frpc config (hot reload, no restart needed):
   ```bash
   curl -X POST http://localhost:3002/api/restart
   ```

### Tunneling to Host Services
Use `host.docker.internal` as `local_host` (enabled via `extra_hosts` in docker-compose.yaml for both containers).

### Updating Tunnel Token
If the server token changes:
1. Update `TUNNEL_TOKEN` in `~/.bash_exports.sh`
2. Reload: `source ~/.bash_exports.sh && docker compose restart frpc`

The `TUNNEL_TOKEN` env var takes priority over `credentials.json`.

## Export/Import Tunnels

Export and import tunnel configurations via the UI buttons or API.

### Export Format
```json
{
  "tunnels": [
    {
      "name": "myapp",
      "type": "http",
      "local_port": 8080,
      "local_host": "127.0.0.1",
      "subdomain": "myapp"
    }
  ]
}
```

### CLI Usage
```bash
# Export tunnels to file
curl -s http://localhost:3002/api/tunnels/export > tunnels.json

# Import tunnels from file
curl -X POST http://localhost:3002/api/tunnels/import \
  -H 'Content-Type: application/json' \
  -d @tunnels.json
```

### Import Response
```json
{
  "created": ["tunnel1", "tunnel2"],
  "failed": [{"name": "tunnel3", "error": "Subdomain already exists"}]
}
```

## Dependencies
- FastAPI + Uvicorn for web server
- Pydantic for request validation
- Requests for server API calls and frpc admin API
- frpc container (`snowdreamtech/frpc:0.52.3`)

## Files
| File | Purpose |
|------|---------|
| `tunnel_client/` | Main Python package |
| `credentials.json` | User credentials (runtime, gitignored) |
| `tunnels.json` | Exported tunnel configs (runtime, gitignored) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build |
| `docker-compose.yaml` | Docker orchestration |
| `install.sh` | Installation script for frpc and systemd |

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
docker compose up -d        # Start in background
docker compose logs -f      # View logs
docker compose down         # Stop
docker compose build --no-cache  # Rebuild
```

### Docker (standalone)
```bash
docker build -t tunnel-client .
docker run -p 3000:3000 -v ./credentials.json:/app/credentials.json tunnel-client
```

### Service management
```bash
sudo systemctl start tunnel-client
sudo systemctl stop tunnel-client
sudo systemctl restart tunnel-client
journalctl -u tunnel-client -f  # View logs
```

## Architecture

### Flow
```
User Login → Server API → access_token + tunnel_token
                ↓
tunnel_client → Server API → Tunnel CRUD
                ↓
             frpc → Server (frps)
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
- **services/frpc.py**: frpc process lifecycle (start, stop, config generation)
- **routers/auth.py**: Authentication endpoints (login saves credentials, auto-starts frpc)
- **routers/tunnels.py**: Tunnel CRUD (proxies to server API)
- **routers/service.py**: frpc service control

### Configuration Files
- **`credentials.json`**: User credentials (auto-created on login, 0600 permissions)
- **`/etc/frp/frpc.ini`**: Auto-generated frpc config with 0600 permissions
- **`/tmp/frpc.log`**: frpc subprocess output for debugging
- **`/tmp/frpc.pid`**: frpc process ID with 0600 permissions

### Key API Endpoints
- `GET /api/config` - Get client configuration (server_url if pre-configured)
- `POST /api/login` - Login to server, save credentials
- `POST /api/logout` - Stop frpc, clear credentials
- `GET /api/auth/status` - Check if authenticated
- `GET /api/tunnels` - List tunnels from server
- `POST /api/tunnels` - Create tunnel on server
- `PUT /api/tunnels/{id}` - Update tunnel on server
- `DELETE /api/tunnels/{id}` - Delete tunnel from server
- `GET /api/status` - Check if frpc is running
- `POST /api/start`, `POST /api/stop`, `POST /api/restart` - Control frpc process

### Environment Variables
- `SERVER_URL` - Pre-configured server URL (hides server URL field in login form)

### Process Management
The app manages the `frpc` subprocess:
- PID stored in `/tmp/frpc.pid` with 0600 permissions
- Uses process group kill for clean shutdown
- Auto-starts on login if tunnels exist
- Auto-starts on app startup if credentials and tunnels exist

### Credentials Caching
- Credentials are cached in memory at startup (`services/credentials.py`)
- If `credentials.json` is updated externally, the container must be restarted to pick up changes
- The frpc config (`/etc/frp/frpc.ini`) is regenerated on each service start from credentials + tunnels

## Docker Networking

When running in Docker, `local_host: 127.0.0.1` refers to the container itself, not the host or other containers.

### Tunneling to Other Containers
1. Connect tunnel-client to the same Docker network as target services:
   ```bash
   docker network connect <network-name> tunnel-client
   ```

2. Update tunnels to use container names as `local_host`:
   ```bash
   curl -X PUT http://localhost:3002/api/tunnels/1 \
     -H 'Content-Type: application/json' \
     -d '{"name":"myapp","type":"http","local_port":5000,"local_host":"my-container-name","subdomain":"myapp"}'
   ```

3. Restart frpc to regenerate config:
   ```bash
   curl -X POST http://localhost:3002/api/restart
   ```

### Tunneling to Host Services
Use `host.docker.internal` as `local_host` (enabled via `extra_hosts` in docker-compose.yaml).

### Updating Tunnel Token
If the server token changes:
1. Update `credentials.json` (volume-mounted from host)
2. Restart container: `docker compose down && docker compose up -d`
3. The frpc config will be regenerated with the new token on startup

## Dependencies
- FastAPI + Uvicorn for web server
- Pydantic for request validation
- Requests for server API calls
- External: `frpc` binary at `/usr/local/bin/frpc`

## Files
| File | Purpose |
|------|---------|
| `tunnel_client/` | Main Python package |
| `credentials.json` | User credentials (runtime) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build |
| `docker-compose.yaml` | Docker orchestration |
| `install.sh` | Installation script for frpc and systemd |

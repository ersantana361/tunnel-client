# Tunnel Client

Web-based client for managing FRP tunnels with a clean interface.

---

## Quick Start (Docker)

```bash
# Clone the repo
git clone <repo-url>
cd tunnel-client

# Set your tunnel token
export TUNNEL_TOKEN="your-token-here"

# Start
docker compose up -d

# Open browser
open http://localhost:3002
```

---

## Features

- **Web UI** - Monitor and manage tunnels at http://localhost:3002
- **Server Authentication** - Login with your tunnel server credentials
- **Hot Reload** - Config changes apply instantly (no restart needed)
- **Docker Architecture** - Separate containers for web UI and frpc
- **Auto-restart** - frpc container auto-recovers from failures

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](./docs/getting-started/) | Installation and first steps |
| [Configuration](./docs/configuration/) | Environment variables and settings |
| [Usage](./docs/usage/) | Web UI and API usage |
| [API Reference](./docs/api/) | REST API endpoints |
| [Architecture](./docs/architecture/) | How it works internally |
| [Troubleshooting](./docs/troubleshooting/) | Common issues and solutions |

---

## Architecture

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

---

## Installation

### Docker Compose (Recommended)

1. Set your tunnel token:
   ```bash
   export TUNNEL_TOKEN="your-token-here"
   ```

2. Start the containers:
   ```bash
   docker compose up -d
   ```

3. Open http://localhost:3002 and login with your server credentials

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVER_URL` | Pre-configured server URL | (none) |
| `TUNNEL_TOKEN` | FRP authentication token | (none) |
| `FRPC_ADMIN_URL` | frpc admin API URL | `http://frpc:7400` |

---

## Usage

### Web UI

Open http://localhost:3002 to:
- Login with your tunnel server credentials
- Create, edit, and delete tunnels
- View tunnel connection status
- Export/import tunnel configurations

### Docker Commands

```bash
docker compose up -d              # Start both containers
docker compose logs -f            # View logs (both containers)
docker compose logs -f frpc       # View frpc logs only
docker compose down               # Stop
docker compose build --no-cache   # Rebuild tunnel-client
docker compose restart frpc       # Restart frpc after token change
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | POST | Login to server |
| `/api/logout` | POST | Logout and stop tunnels |
| `/api/tunnels` | GET | List all tunnels |
| `/api/tunnels` | POST | Create a tunnel |
| `/api/tunnels/{id}` | PUT | Update a tunnel |
| `/api/tunnels/{id}` | DELETE | Delete a tunnel |
| `/api/status` | GET | Check frpc status |
| `/api/restart` | POST | Reload frpc config |

---

## Updating Tunnel Token

If the server token changes:

1. Update `TUNNEL_TOKEN` in `~/.bash_exports.sh` (or your env file)
2. Reload: `source ~/.bash_exports.sh && docker compose restart frpc`

---

## Tunneling to Other Containers

1. Connect frpc to the target network:
   ```bash
   docker network connect <network-name> frpc
   ```

2. Update tunnel `local_host` to use container name:
   ```bash
   curl -X PUT http://localhost:3002/api/tunnels/1 \
     -H 'Content-Type: application/json' \
     -d '{"name":"myapp","type":"http","local_port":5000,"local_host":"my-container","subdomain":"myapp"}'
   ```

3. Reload config:
   ```bash
   curl -X POST http://localhost:3002/api/restart
   ```

---

## Tunneling to Host Services

Use `host.docker.internal` as `local_host` to tunnel to services running on your host machine.

---

## Files

| File | Purpose |
|------|---------|
| `tunnel_client/` | Python web application |
| `docker-compose.yaml` | Container orchestration |
| `Dockerfile` | tunnel-client container build |
| `credentials.json` | Saved login credentials (gitignored) |
| `/etc/frp/frpc.toml` | Generated frpc config (in volume) |

---

## See Also

- [CLAUDE.md](./CLAUDE.md) - AI assistant guide
- [FRP Project](https://github.com/fatedier/frp) - Fast Reverse Proxy
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

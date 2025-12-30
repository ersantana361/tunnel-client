# Architecture Overview

This document describes how Tunnel Client works internally.

---

## Docker Container Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐      ┌─────────────────────┐           │
│  │   tunnel-client     │      │        frpc         │           │
│  │   (Web UI + API)    │      │   (Tunnel Proxy)    │           │
│  │                     │      │                     │           │
│  │  - FastAPI server   │      │  - frpc binary      │           │
│  │  - Config generator │─────►│  - Admin API :7400  │           │
│  │  - Server API client│      │  - Always running   │           │
│  │  - Port 3000        │      │                     │           │
│  └──────────┬──────────┘      └──────────┬──────────┘           │
│             │                            │                       │
│             ▼                            ▼                       │
│       /etc/frp/frpc.toml           frps server                  │
│       (shared volume)              (remote)                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### tunnel-client Container

The web application container running FastAPI:

| Component | Purpose |
|-----------|---------|
| `main.py` | Application entry point, lifespan management |
| `routers/auth.py` | Login/logout endpoints |
| `routers/tunnels.py` | Tunnel CRUD operations |
| `routers/service.py` | frpc status and reload |
| `services/frpc.py` | Config generation, admin API client |
| `services/credentials.py` | Credential storage |
| `services/api_client.py` | Tunnel server API client |

### frpc Container

Official frpc image (`snowdreamtech/frpc:0.52.3`):

- Runs the frpc binary continuously
- Reads config from shared volume `/etc/frp/frpc.toml`
- Exposes admin API on port 7400
- Auto-restarts on failure (`restart: unless-stopped`)

### Shared Volume

The `frpc-config` volume at `/etc/frp`:

- Contains `frpc.toml` (TOML format)
- Written by tunnel-client
- Read by frpc container
- Persists across restarts

---

## Data Flow

### Login Flow

```
1. User enters credentials in Web UI
   │
   ▼
2. POST /api/login → tunnel-client
   │
   ▼
3. Forward to tunnel server API
   │
   ▼
4. Receive access_token + tunnel_token
   │
   ▼
5. Save to credentials.json
   │
   ▼
6. Fetch tunnels from server
   │
   ▼
7. Generate frpc.toml config
   │
   ▼
8. Call frpc admin API to reload
   │
   ▼
9. frpc connects to frps server
```

### Tunnel Change Flow

```
1. User creates/updates tunnel via UI
   │
   ▼
2. POST/PUT /api/tunnels → tunnel-client
   │
   ▼
3. Forward to tunnel server API
   │
   ▼
4. Regenerate frpc.toml
   │
   ▼
5. GET http://frpc:7400/api/reload
   │
   ▼
6. frpc hot-reloads config (no restart)
```

---

## Configuration Files

### credentials.json

Stored in the tunnel-client container:

```json
{
  "server_url": "http://tunnel.example.com:8000",
  "access_token": "jwt-token-here",
  "tunnel_token": "frp-auth-token",
  "user_email": "user@example.com"
}
```

### frpc.toml

Generated TOML config in shared volume:

```toml
serverAddr = "tunnel.example.com"
serverPort = 7000
auth.token = "frp-auth-token"

webServer.addr = "0.0.0.0"
webServer.port = 7400

[[proxies]]
name = "my-app"
type = "http"
localIP = "host.docker.internal"
localPort = 8080
subdomain = "myapp"
```

---

## API Architecture

### External APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Web UI (HTML) |
| `POST /api/login` | POST | Authenticate with server |
| `POST /api/logout` | POST | Clear credentials, mark offline |
| `GET /api/tunnels` | GET | List tunnels from server |
| `POST /api/tunnels` | POST | Create tunnel on server |
| `PUT /api/tunnels/{id}` | PUT | Update tunnel on server |
| `DELETE /api/tunnels/{id}` | DELETE | Delete tunnel from server |
| `GET /api/status` | GET | frpc connection status |
| `POST /api/restart` | POST | Regenerate config, reload frpc |

### Internal APIs

| Endpoint | Container | Purpose |
|----------|-----------|---------|
| `http://frpc:7400/api/status` | frpc | Get proxy status |
| `http://frpc:7400/api/reload` | frpc | Hot-reload config |

---

## Environment Variables

| Variable | Container | Purpose |
|----------|-----------|---------|
| `SERVER_URL` | tunnel-client | Pre-configured server URL |
| `TUNNEL_TOKEN` | tunnel-client | Override tunnel token |
| `FRPC_ADMIN_URL` | tunnel-client | frpc admin API URL |

---

## Security Model

### Network Isolation

- tunnel-client exposes port 3002 (mapped from 3000)
- frpc admin API (7400) only accessible within Docker network
- frpc connects outbound to frps server

### Credential Storage

- `credentials.json` stored with 0600 permissions
- `frpc.toml` stored with 0600 permissions
- Tokens passed via environment variables

### Authentication

- Web UI requires login to tunnel server
- JWT access_token for API calls
- tunnel_token for frpc-to-frps authentication

---

## File Structure

```
tunnel-client/
├── tunnel_client/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan
│   ├── config.py            # Environment variables
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── credentials.py   # Credential management
│   │   ├── frpc.py          # Config generation, admin API
│   │   └── api_client.py    # Tunnel server API
│   ├── routers/
│   │   ├── auth.py          # Login/logout
│   │   ├── tunnels.py       # Tunnel CRUD
│   │   └── service.py       # frpc control
│   ├── static/              # CSS, JS
│   └── templates/           # HTML templates
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
└── credentials.json         # Runtime, gitignored
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| Validation | Pydantic |
| HTTP Client | Requests |
| Tunnel Proxy | frpc (FRP) |
| Container | Docker |

---

[Back to Documentation](../)

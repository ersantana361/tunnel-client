# Architecture Overview

This document describes how Tunnel Client works internally, its components, and data flow.

---

## Table of Contents

- [System Overview](#system-overview)
- [Components](#components)
- [Data Flow](#data-flow)
- [File Structure](#file-structure)
- [Configuration Flow](#configuration-flow)
- [Process Management](#process-management)
- [API Architecture](#api-architecture)
- [Security Model](#security-model)
- [Extending the System](#extending-the-system)

---

## System Overview

Tunnel Client is a web-based management interface for [FRP (Fast Reverse Proxy)](https://github.com/fatedier/frp). It reads tunnel definitions from a YAML file, generates frpc configuration, and manages the frpc process.

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User                                  │
│                          │                                   │
│          ┌───────────────┼───────────────┐                   │
│          ▼               ▼               ▼                   │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│    │  Web UI  │    │   CLI    │    │   API    │             │
│    │ (Browser)│    │ (curl)   │    │ (Script) │             │
│    └────┬─────┘    └────┬─────┘    └────┬─────┘             │
│         │               │               │                    │
│         └───────────────┼───────────────┘                    │
│                         ▼                                    │
│              ┌────────────────────┐                          │
│              │      FastAPI       │                          │
│              │      (app.py)      │                          │
│              └─────────┬──────────┘                          │
│                        │                                     │
│         ┌──────────────┼──────────────┐                      │
│         ▼              ▼              ▼                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │  YAML      │ │  frpc.ini  │ │   frpc     │               │
│  │  Config    │ │  Generator │ │  Process   │               │
│  └────────────┘ └────────────┘ └────────────┘               │
│                                      │                       │
│                                      ▼                       │
│                           ┌────────────────┐                 │
│                           │  Tunnel Server │                 │
│                           │   (Remote)     │                 │
│                           └────────────────┘                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. FastAPI Application (`app.py`)

The core of the system, handling:
- HTTP request routing
- Configuration loading
- frpc.ini generation
- Process management
- Web UI serving

**Key responsibilities**:
- Serve REST API endpoints
- Serve embedded HTML/CSS/JS UI
- Manage frpc subprocess lifecycle
- Read and cache YAML configuration

### 2. YAML Configuration (`tunnels.yaml`)

User-facing configuration file defining:
- Server connection (URL, token)
- Tunnel definitions

**Characteristics**:
- Human-readable format
- Validated on load
- Cached in memory
- Hot-reloadable

### 3. frpc Configuration Generator

Transforms YAML config into frpc.ini format.

**Input** (YAML):
```yaml
server:
  url: "server.com:7000"
  token: "abc123"
tunnels:
  - name: web
    type: http
    local_port: 8080
    subdomain: app
```

**Output** (`/etc/frp/frpc.ini`):
```ini
[common]
server_addr = server.com
server_port = 7000
token = abc123

[web]
type = http
local_ip = 127.0.0.1
local_port = 8080
subdomain = app
```

### 4. frpc Process Manager

Controls the frpc subprocess:
- Start with proper arguments
- Monitor via PID file
- Graceful shutdown
- Process group management

### 5. Web UI

Single-page application embedded in Python:
- Pure HTML/CSS/JavaScript
- No external dependencies
- Communicates via REST API
- Auto-refreshing status

---

## Data Flow

### Startup Flow

```
1. Application starts
   │
   ▼
2. Load tunnels.yaml
   │
   ├─ Not found → Show "No Config" screen
   │
   ▼
3. Cache configuration
   │
   ▼
4. Check for existing frpc process
   │
   ├─ Running → Note PID
   │
   ▼
5. Start Uvicorn server
   │
   ▼
6. Ready to serve requests
```

### Request Flow

```
                    HTTP Request
                         │
                         ▼
              ┌──────────────────┐
              │  FastAPI Router  │
              └────────┬─────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
   GET /           GET /api/*     POST /api/*
       │               │               │
       ▼               ▼               ▼
  Return HTML    Read State      Modify State
                       │               │
                       ▼               ▼
              ┌────────────────────────────┐
              │   Configuration Cache      │
              │   Process State           │
              └────────────────────────────┘
```

### Tunnel Creation Flow

```
1. User edits tunnels.yaml
   │
   ▼
2. User clicks "Reload Config"
   │
   ▼
3. POST /api/reload
   │
   ▼
4. Reload YAML file
   │
   ▼
5. Update cache
   │
   ▼
6. Regenerate frpc.ini
   │
   ▼
7. If frpc running → Restart
   │
   ▼
8. Return success
```

---

## File Structure

### Project Files

```
tunnel-client/
├── app.py                 # Main application (single file)
├── tunnels.yaml           # User configuration
├── tunnels.example.yaml   # Example configuration
├── requirements.txt       # Python dependencies
├── install.sh             # Installation script
├── README.md              # Project readme
├── CLAUDE.md              # AI assistant guide
└── docs/                  # Documentation
    ├── README.md          # Docs index
    ├── getting-started/
    ├── configuration/
    ├── usage/
    ├── api/
    ├── examples/
    ├── troubleshooting/
    └── architecture/
```

### Runtime Files

| File | Location | Purpose | Permissions |
|------|----------|---------|-------------|
| frpc.ini | `/etc/frp/frpc.ini` | frpc configuration | 0600 |
| frpc.pid | `/tmp/frpc.pid` | Process ID | 0600 |
| frpc.log | `/tmp/frpc.log` | frpc output | 0644 |

### Configuration Constants

```python
CONFIG_FILE = "tunnels.yaml"      # YAML config location
FRPC_CONFIG = "/etc/frp/frpc.ini" # Generated config
FRPC_PID_FILE = "/tmp/frpc.pid"   # PID file
FRPC_LOG_FILE = "/tmp/frpc.log"   # Log file
```

---

## Configuration Flow

### Loading Configuration

```python
# On startup or reload
def load_config(config_path=None):
    path = config_path or CONFIG_FILE
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    _config_cache = config
    return config
```

### Configuration Cache

- Loaded once at startup
- Cached in global `_config_cache`
- Invalidated on reload
- Thread-safe (GIL protected)

### Generating frpc.ini

```python
async def regenerate_frpc_config():
    config = get_cached_config()

    # Extract server settings
    server = config.get('server', {})
    server_addr = parse_url(server['url'])

    # Build config content
    content = f"""[common]
server_addr = {server_addr}
server_port = {server_port}
token = {server['token']}
"""

    # Add each tunnel
    for tunnel in config.get('tunnels', []):
        content += generate_tunnel_section(tunnel)

    # Write with secure permissions
    with open(FRPC_CONFIG, 'w') as f:
        f.write(content)
    os.chmod(FRPC_CONFIG, 0o600)
```

---

## Process Management

### Starting frpc

```python
async def start_service():
    # Check not already running
    status = await get_status()
    if status["running"]:
        raise HTTPException(400, "Already running")

    # Generate config
    await regenerate_frpc_config()

    # Start process
    process = subprocess.Popen(
        ["/usr/local/bin/frpc", "-c", FRPC_CONFIG],
        stdout=log_file,
        stderr=log_file,
        start_new_session=True  # Process group
    )

    # Save PID
    with open(FRPC_PID_FILE, 'w') as f:
        f.write(str(process.pid))
```

### Stopping frpc

```python
async def stop_service():
    pid = get_current_pid()

    # Kill process group for clean shutdown
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
    except:
        os.kill(pid, signal.SIGTERM)

    # Wait for termination
    for _ in range(50):  # 5 seconds
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except OSError:
            break

    # Cleanup PID file
    os.remove(FRPC_PID_FILE)
```

### Status Checking

```python
async def get_status():
    if not os.path.exists(FRPC_PID_FILE):
        return {"running": False, "pid": None}

    pid = int(open(FRPC_PID_FILE).read())

    try:
        os.kill(pid, 0)  # Check if alive
        return {"running": True, "pid": pid}
    except OSError:
        os.remove(FRPC_PID_FILE)  # Stale
        return {"running": False, "pid": None}
```

---

## API Architecture

### Endpoint Structure

```
GET  /              → HTML UI
GET  /api/config    → Configuration info
GET  /api/tunnels   → Tunnel list
GET  /api/status    → Service status
POST /api/start     → Start frpc
POST /api/stop      → Stop frpc
POST /api/restart   → Restart frpc
POST /api/reload    → Reload config
```

### Response Format

All API responses are JSON:

```json
{
  "key": "value",
  "nested": {
    "data": "here"
  }
}
```

Errors follow FastAPI format:

```json
{
  "detail": "Error message"
}
```

### Middleware

- **CORS**: Not configured (local access only)
- **Authentication**: None (relies on localhost binding)
- **Logging**: Request logging via uvicorn

---

## Security Model

### Access Control

| Control | Implementation |
|---------|----------------|
| Network binding | `127.0.0.1` by default |
| File permissions | Config 0600, PID 0600 |
| Token storage | In YAML file (user-managed) |

### Recommendations

1. **Never expose to internet**: Use `127.0.0.1` only
2. **Protect tunnels.yaml**: Contains secrets
3. **Add to .gitignore**: Prevent token commits
4. **Use strong tokens**: Get from admin

### File Permission Hardening

```python
# Config file
os.chmod(FRPC_CONFIG, stat.S_IRUSR | stat.S_IWUSR)  # 0600

# PID file
os.chmod(FRPC_PID_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
```

---

## Extending the System

### Adding a New Endpoint

```python
@app.get("/api/new-endpoint")
async def new_endpoint():
    """Description of endpoint"""
    return {"key": "value"}
```

### Adding Tunnel Types

1. Update YAML schema
2. Update frpc.ini generator
3. Update validation
4. Update UI (if needed)

### Adding Configuration Options

1. Define in YAML structure
2. Update `load_config()` to read it
3. Update `regenerate_frpc_config()` to use it
4. Document in configuration guide

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| Validation | Pydantic |
| Config Parsing | PyYAML |
| Process Management | subprocess, os |
| Frontend | Vanilla HTML/CSS/JS |
| Tunnel Proxy | frpc (FRP client) |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Troubleshooting](../troubleshooting/) | [Documentation Index](../) | [Getting Started](../getting-started/) |

---

[Back to Index](../) | [Getting Started](../getting-started/) | [Configuration](../configuration/) | [API Reference](../api/)

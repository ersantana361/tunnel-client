# Getting Started

This guide will help you install and set up Tunnel Client.

---

## Prerequisites

- Docker and Docker Compose
- Tunnel server URL and credentials
- Tunnel token (from server admin)

---

## Installation

### Step 1: Clone the Repository

```bash
git clone <repo-url>
cd tunnel-client
```

### Step 2: Set Environment Variables

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.bash_exports.sh`):

```bash
export TUNNEL_TOKEN="your-tunnel-token-here"
```

Then source it:

```bash
source ~/.bashrc  # or your profile file
```

### Step 3: Start the Containers

```bash
docker compose up -d
```

This starts two containers:
- **tunnel-client** - Web UI on port 3002
- **frpc** - Tunnel proxy (always running)

### Step 4: Login

1. Open http://localhost:3002
2. Enter your tunnel server URL (e.g., `http://tunnel.example.com:8000`)
3. Login with your email and password

---

## Quick Start

### Create Your First Tunnel

1. Click "Add Tunnel" in the web UI
2. Fill in the details:
   - **Name**: `my-app`
   - **Type**: `http`
   - **Local Port**: `8080`
   - **Subdomain**: `myapp`
3. Click "Create"

### Test the Tunnel

Start a local server:

```bash
python3 -m http.server 8080
```

Access via tunnel:

```
http://myapp.your-server.com
```

---

## Docker Commands

```bash
# Start containers
docker compose up -d

# View logs
docker compose logs -f

# View frpc logs only
docker compose logs -f frpc

# Stop containers
docker compose down

# Rebuild after code changes
docker compose build --no-cache

# Restart frpc after token change
source ~/.bash_exports.sh && docker compose restart frpc
```

---

## Verifying Installation

### Check Container Status

```bash
docker compose ps
```

Expected output:
```
NAME             STATUS
tunnel-client    Up
frpc             Up
```

### Check frpc Connection

```bash
curl http://localhost:3002/api/status
```

Expected output:
```json
{
  "running": true,
  "proxies": { ... }
}
```

### Check Logs

```bash
docker compose logs -f frpc
```

Look for:
```
login to server success
start proxy success
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs tunnel-client

# Rebuild
docker compose build --no-cache && docker compose up -d
```

### Token Mismatch Error

```bash
# Update token in your env file
export TUNNEL_TOKEN="new-token"

# Restart frpc
docker compose restart frpc
```

### frpc Not Connecting

Check if server is reachable:

```bash
docker compose logs -f frpc
```

If you see "connection refused", verify your server URL.

---

## Next Steps

- [Configuration](../configuration/) - Environment variables
- [Usage](../usage/) - Web UI and API
- [Tunneling to Containers](../configuration/#tunneling-to-other-containers) - Docker networking

---

[Back to Documentation](../)

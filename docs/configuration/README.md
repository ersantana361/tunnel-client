# Configuration Guide

This guide covers environment variables and tunnel configuration.

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `TUNNEL_TOKEN` | FRP authentication token (from server admin) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | (none) | Pre-configured server URL (hides URL field in login) |
| `FRPC_ADMIN_URL` | `http://frpc:7400` | frpc admin API URL |
| `FRPC_CONFIG` | `/etc/frp/frpc.toml` | Path to generated frpc config |
| `CREDENTIALS_FILE` | `credentials.json` | Path to saved credentials |

### Setting Environment Variables

Add to `~/.bash_exports.sh` or your shell profile:

```bash
export TUNNEL_TOKEN="your-token-here"
```

Then source it:

```bash
source ~/.bash_exports.sh
```

---

## Tunnel Configuration

Tunnels are managed via the web UI or API, stored on the tunnel server.

### Tunnel Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Unique identifier |
| `type` | string | Yes | `http`, `https`, `tcp`, or `udp` |
| `local_port` | integer | Yes | Port on local machine (1-65535) |
| `local_host` | string | No | Host to connect to (default: `127.0.0.1`) |
| `subdomain` | string | http/https | Subdomain for routing |
| `remote_port` | integer | tcp/udp | Port exposed on server |

### Tunnel Types

| Type | Use Case | Required Field |
|------|----------|----------------|
| `http` | Web apps, APIs | `subdomain` |
| `https` | Secure web traffic | `subdomain` |
| `tcp` | Databases, SSH | `remote_port` |
| `udp` | Gaming, streaming | `remote_port` |

---

## Docker Networking

### Tunneling to Host Services

Use `host.docker.internal` as `local_host`:

```bash
curl -X PUT http://localhost:3002/api/tunnels/1 \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "my-app",
    "type": "http",
    "local_port": 8080,
    "local_host": "host.docker.internal",
    "subdomain": "myapp"
  }'
```

### Tunneling to Other Containers

1. Connect frpc to the target network:
   ```bash
   docker network connect <network-name> frpc
   ```

2. Use container name as `local_host`:
   ```bash
   curl -X PUT http://localhost:3002/api/tunnels/1 \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "my-app",
       "type": "http",
       "local_port": 5000,
       "local_host": "flask-container",
       "subdomain": "myapp"
     }'
   ```

3. Reload config:
   ```bash
   curl -X POST http://localhost:3002/api/restart
   ```

### local_host Reference

| Scenario | local_host Value |
|----------|------------------|
| Service on host machine | `host.docker.internal` |
| Service in same Docker network | Container name |
| Service in different network | Connect networks first, then container name |

---

## Updating Tunnel Token

If the server token changes:

1. Update `TUNNEL_TOKEN` in your env file
2. Reload:
   ```bash
   source ~/.bash_exports.sh && docker compose restart frpc
   ```

---

## Generated Config

The tunnel-client generates `/etc/frp/frpc.toml` in TOML format:

```toml
serverAddr = "tunnel.example.com"
serverPort = 7000
auth.token = "your-token"

webServer.addr = "0.0.0.0"
webServer.port = 7400

[[proxies]]
name = "my-app"
type = "http"
localIP = "host.docker.internal"
localPort = 8080
subdomain = "myapp"
```

This is auto-generated - do not edit manually.

---

[Back to Documentation](../)

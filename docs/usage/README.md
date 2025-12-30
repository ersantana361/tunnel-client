# Usage Guide

How to use Tunnel Client on a daily basis.

---

## Web UI

### Accessing the UI

Open http://localhost:3002 in your browser.

### Login

1. Enter your tunnel server URL (e.g., `http://tunnel.example.com:8000`)
2. Enter your email and password
3. Click "Login"

### Dashboard

After login you'll see:
- Connection status (green = connected)
- List of your tunnels
- Buttons to add, edit, delete tunnels
- Export/Import buttons

### Managing Tunnels

#### Create a Tunnel

1. Click "Add Tunnel"
2. Fill in:
   - **Name**: Unique identifier (e.g., `my-app`)
   - **Type**: `http`, `https`, `tcp`, or `udp`
   - **Local Port**: Port your service runs on (e.g., `8080`)
   - **Local Host**: Usually `host.docker.internal` for host services
   - **Subdomain** (for http/https): e.g., `myapp` → `myapp.tunnel.example.com`
3. Click "Create"

#### Edit a Tunnel

1. Click the edit icon on the tunnel card
2. Update fields
3. Click "Save"

#### Delete a Tunnel

1. Click the delete icon on the tunnel card
2. Confirm deletion

---

## API Usage

All API endpoints are at `http://localhost:3002/api/`.

### Authentication

```bash
# Login
curl -X POST http://localhost:3002/api/login \
  -H 'Content-Type: application/json' \
  -d '{"server_url":"http://tunnel.example.com:8000","email":"user@example.com","password":"pass"}'

# Check auth status
curl http://localhost:3002/api/auth/status

# Logout
curl -X POST http://localhost:3002/api/logout
```

### Tunnels

```bash
# List tunnels
curl http://localhost:3002/api/tunnels

# Create tunnel
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-app","type":"http","local_port":8080,"local_host":"host.docker.internal","subdomain":"myapp"}'

# Update tunnel
curl -X PUT http://localhost:3002/api/tunnels/1 \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-app","type":"http","local_port":9000,"local_host":"host.docker.internal","subdomain":"myapp"}'

# Delete tunnel
curl -X DELETE http://localhost:3002/api/tunnels/1
```

### Service Control

```bash
# Check status
curl http://localhost:3002/api/status

# Reload config (after tunnel changes)
curl -X POST http://localhost:3002/api/restart
```

### Export/Import

```bash
# Export tunnels to file
curl http://localhost:3002/api/tunnels/export > tunnels.json

# Import tunnels from file
curl -X POST http://localhost:3002/api/tunnels/import \
  -H 'Content-Type: application/json' \
  -d @tunnels.json
```

---

## Docker Commands

### Start/Stop

```bash
# Start both containers
docker compose up -d

# Stop both containers
docker compose down

# Restart frpc (after token change)
docker compose restart frpc

# Restart tunnel-client
docker compose restart tunnel-client
```

### Viewing Logs

```bash
# All containers
docker compose logs -f

# frpc only
docker compose logs -f frpc

# tunnel-client only
docker compose logs -f tunnel-client

# Last 50 lines
docker compose logs --tail 50
```

### Rebuild

```bash
# After code changes
docker compose build --no-cache && docker compose up -d
```

---

## Common Operations

| Task | How To |
|------|--------|
| Add tunnel | Web UI → "Add Tunnel" |
| Edit tunnel | Web UI → Click edit icon |
| Delete tunnel | Web UI → Click delete icon |
| Check status | `curl http://localhost:3002/api/status` |
| Reload config | `curl -X POST http://localhost:3002/api/restart` |
| Update token | Update env, `docker compose restart frpc` |
| View logs | `docker compose logs -f frpc` |

---

## Networking Tips

### Tunneling to Host Services

Use `host.docker.internal` as `local_host`:

```json
{
  "name": "my-app",
  "type": "http",
  "local_port": 8080,
  "local_host": "host.docker.internal",
  "subdomain": "myapp"
}
```

### Tunneling to Other Containers

1. Connect frpc to the target network:
   ```bash
   docker network connect my-network frpc
   ```

2. Use container name as `local_host`:
   ```json
   {
     "name": "my-app",
     "local_host": "flask-container",
     ...
   }
   ```

---

[Back to Documentation](../)

# API Reference

REST API endpoints for Tunnel Client.

---

## Base URL

```
http://localhost:3002
```

---

## Authentication

### POST /api/login

Login to tunnel server.

**Request**:
```json
{
  "server_url": "http://tunnel.example.com:8000",
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response** (200):
```json
{
  "message": "Login successful",
  "user_email": "user@example.com"
}
```

### GET /api/auth/status

Check if authenticated.

**Response**:
```json
{
  "authenticated": true,
  "server_url": "http://tunnel.example.com:8000",
  "user_email": "user@example.com"
}
```

### POST /api/logout

Logout and clear credentials.

**Response**:
```json
{
  "message": "Logged out"
}
```

---

## Tunnels

### GET /api/tunnels

List all tunnels from server.

**Response**:
```json
[
  {
    "id": 1,
    "name": "my-app",
    "type": "http",
    "local_port": 8080,
    "local_host": "host.docker.internal",
    "subdomain": "myapp",
    "is_online": true
  }
]
```

### POST /api/tunnels

Create a new tunnel.

**Request**:
```json
{
  "name": "my-app",
  "type": "http",
  "local_port": 8080,
  "local_host": "host.docker.internal",
  "subdomain": "myapp"
}
```

**Response** (201):
```json
{
  "id": 1,
  "name": "my-app",
  "type": "http",
  "local_port": 8080,
  "local_host": "host.docker.internal",
  "subdomain": "myapp"
}
```

### PUT /api/tunnels/{id}

Update a tunnel.

**Request**:
```json
{
  "name": "my-app",
  "type": "http",
  "local_port": 9000,
  "local_host": "host.docker.internal",
  "subdomain": "myapp"
}
```

### DELETE /api/tunnels/{id}

Delete a tunnel.

**Response** (200):
```json
{
  "message": "Tunnel deleted"
}
```

---

## Export/Import

### GET /api/tunnels/export

Export all tunnels as JSON.

**Response**:
```json
{
  "tunnels": [
    {
      "name": "my-app",
      "type": "http",
      "local_port": 8080,
      "local_host": "host.docker.internal",
      "subdomain": "myapp"
    }
  ]
}
```

### POST /api/tunnels/import

Import tunnels from JSON.

**Request**:
```json
{
  "tunnels": [
    {
      "name": "my-app",
      "type": "http",
      "local_port": 8080,
      "subdomain": "myapp"
    }
  ]
}
```

**Response**:
```json
{
  "created": ["my-app"],
  "failed": []
}
```

---

## Service Control

### GET /api/status

Check frpc status via admin API.

**Response**:
```json
{
  "running": true,
  "proxies": {
    "http": [
      {
        "name": "my-app",
        "status": "running",
        "local_addr": "host.docker.internal:8080",
        "remote_addr": "myapp.tunnel.example.com:8080"
      }
    ]
  }
}
```

### POST /api/start

Regenerate config and reload frpc.

**Response**:
```json
{
  "message": "Config reloaded"
}
```

### POST /api/stop

Mark tunnels offline (frpc keeps running).

**Response**:
```json
{
  "message": "Tunnels marked offline"
}
```

### POST /api/restart

Regenerate config and reload frpc.

**Response**:
```json
{
  "message": "Config reloaded"
}
```

---

## Configuration

### GET /api/config

Get client configuration.

**Response**:
```json
{
  "server_url": "http://tunnel.example.com:8000"
}
```

---

## Error Responses

All errors return JSON:

```json
{
  "detail": "Error message"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Server Error |

---

## Examples

### cURL Workflow

```bash
# Login
curl -X POST http://localhost:3002/api/login \
  -H 'Content-Type: application/json' \
  -d '{"server_url":"http://tunnel.example.com:8000","email":"user@example.com","password":"pass"}'

# List tunnels
curl http://localhost:3002/api/tunnels

# Create tunnel
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{"name":"test","type":"http","local_port":8080,"local_host":"host.docker.internal","subdomain":"test"}'

# Check status
curl http://localhost:3002/api/status

# Reload config
curl -X POST http://localhost:3002/api/restart

# Export
curl http://localhost:3002/api/tunnels/export > tunnels.json

# Import
curl -X POST http://localhost:3002/api/tunnels/import \
  -H 'Content-Type: application/json' \
  -d @tunnels.json
```

---

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/login` | POST | Login to server |
| `/api/logout` | POST | Logout |
| `/api/auth/status` | GET | Check auth |
| `/api/tunnels` | GET | List tunnels |
| `/api/tunnels` | POST | Create tunnel |
| `/api/tunnels/{id}` | PUT | Update tunnel |
| `/api/tunnels/{id}` | DELETE | Delete tunnel |
| `/api/tunnels/export` | GET | Export tunnels |
| `/api/tunnels/import` | POST | Import tunnels |
| `/api/status` | GET | frpc status |
| `/api/restart` | POST | Reload frpc |

---

[Back to Documentation](../)

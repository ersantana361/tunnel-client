# API Reference

This document describes the REST API endpoints provided by Tunnel Client.

---

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
  - [GET /](#get-)
  - [GET /api/config](#get-apiconfig)
  - [GET /api/tunnels](#get-apitunnels)
  - [GET /api/status](#get-apistatus)
  - [POST /api/start](#post-apistart)
  - [POST /api/stop](#post-apistop)
  - [POST /api/restart](#post-apirestart)
  - [POST /api/reload](#post-apireload)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Overview

The API provides:
- **Configuration info** - Server and tunnel details
- **Status monitoring** - frpc service state
- **Service control** - Start, stop, restart frpc
- **Hot reload** - Reload config without restart

All responses are JSON unless otherwise noted.

---

## Base URL

```
http://127.0.0.1:3000
```

If you changed the port:
```
http://127.0.0.1:{port}
```

---

## Endpoints

### GET /

Returns the web UI HTML page.

**Response**: `text/html`

```bash
curl http://127.0.0.1:3000/
```

---

### GET /api/config

Returns current configuration information.

**Response**:

```json
{
  "configured": true,
  "config_file": "tunnels.yaml",
  "server_url": "your-server.com:7000",
  "tunnel_count": 3
}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `configured` | boolean | Whether config file exists and is valid |
| `config_file` | string | Path to configuration file |
| `server_url` | string | Configured server URL |
| `tunnel_count` | integer | Number of tunnels defined |

**Example**:

```bash
curl http://127.0.0.1:3000/api/config
```

**Response when not configured**:

```json
{
  "configured": false,
  "config_file": "tunnels.yaml",
  "server_url": "",
  "tunnel_count": 0
}
```

---

### GET /api/tunnels

Returns all tunnels from the configuration file.

**Response**:

```json
{
  "tunnels": [
    {
      "name": "my-api",
      "description": "REST API",
      "type": "http",
      "local_port": 8080,
      "subdomain": "api"
    },
    {
      "name": "postgres",
      "description": "Database",
      "type": "tcp",
      "local_port": 5432,
      "remote_port": 15432
    }
  ],
  "config_file": "tunnels.yaml"
}
```

**Tunnel Fields**:

| Field | Type | Presence | Description |
|-------|------|----------|-------------|
| `name` | string | Always | Unique tunnel identifier |
| `description` | string | Optional | Human-readable description |
| `type` | string | Always | `http`, `https`, `tcp`, or `udp` |
| `local_port` | integer | Always | Local port number |
| `subdomain` | string | HTTP/HTTPS | Subdomain for routing |
| `remote_port` | integer | TCP/UDP | Remote port mapping |

**Example**:

```bash
curl http://127.0.0.1:3000/api/tunnels
```

**Response when no tunnels**:

```json
{
  "tunnels": [],
  "config_file": "tunnels.yaml"
}
```

---

### GET /api/status

Returns the current frpc service status.

**Response**:

```json
{
  "running": true,
  "pid": 12345
}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `running` | boolean | Whether frpc is currently running |
| `pid` | integer/null | Process ID if running, null if not |

**Example**:

```bash
curl http://127.0.0.1:3000/api/status
```

**Response when not running**:

```json
{
  "running": false,
  "pid": null
}
```

---

### POST /api/start

Starts the frpc service.

**Request**: No body required

**Response** (200 OK):

```json
{
  "message": "Service started",
  "pid": 12345
}
```

**Error Responses**:

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"detail": "Already running"}` | Service is already running |
| 500 | `{"detail": "frpc not found..."}` | frpc binary not installed |
| 500 | `{"detail": "..."}` | Other startup errors |

**Example**:

```bash
curl -X POST http://127.0.0.1:3000/api/start
```

---

### POST /api/stop

Stops the frpc service.

**Request**: No body required

**Response** (200 OK):

```json
{
  "message": "Service stopped"
}
```

**Error Responses**:

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"detail": "Not running"}` | Service is not running |
| 500 | `{"detail": "..."}` | Stop errors |

**Example**:

```bash
curl -X POST http://127.0.0.1:3000/api/stop
```

---

### POST /api/restart

Restarts the frpc service (stop + start).

**Request**: No body required

**Response** (200 OK):

```json
{
  "message": "Service restarted"
}
```

**Behavior**:
- If running: stops then starts
- If not running: just starts

**Example**:

```bash
curl -X POST http://127.0.0.1:3000/api/restart
```

---

### POST /api/reload

Reloads configuration from the YAML file.

**Request**: No body required

**Response** (200 OK):

```json
{
  "message": "Configuration reloaded",
  "tunnel_count": 5
}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Success message |
| `tunnel_count` | integer | Number of tunnels after reload |

**Error Responses**:

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"detail": "Failed to reload..."}` | Config file missing or invalid |

**Behavior**:
1. Re-reads `tunnels.yaml`
2. Updates internal cache
3. Regenerates `frpc.ini`
4. If frpc running, restarts it

**Example**:

```bash
curl -X POST http://127.0.0.1:3000/api/reload
```

---

## Error Handling

### Error Response Format

All errors return JSON with a `detail` field:

```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid input, already running, etc.) |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

### Validation Errors

When request validation fails (422):

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Examples

### Shell Script: Health Check

```bash
#!/bin/bash
# health-check.sh

STATUS=$(curl -s http://127.0.0.1:3000/api/status)
RUNNING=$(echo $STATUS | jq -r '.running')

if [ "$RUNNING" = "true" ]; then
    echo "Tunnel client is healthy"
    exit 0
else
    echo "Tunnel client is not running"
    exit 1
fi
```

### Python: Start Service

```python
import requests

def start_tunnel():
    response = requests.post('http://127.0.0.1:3000/api/start')
    if response.status_code == 200:
        data = response.json()
        print(f"Started with PID: {data['pid']}")
    else:
        print(f"Error: {response.json()['detail']}")

start_tunnel()
```

### JavaScript: Monitor Status

```javascript
async function checkStatus() {
    const response = await fetch('http://127.0.0.1:3000/api/status');
    const data = await response.json();

    if (data.running) {
        console.log(`Running (PID: ${data.pid})`);
    } else {
        console.log('Not running');
    }
}

// Check every 5 seconds
setInterval(checkStatus, 5000);
```

### cURL: Complete Workflow

```bash
# Check initial status
curl -s http://127.0.0.1:3000/api/status | jq

# View tunnels
curl -s http://127.0.0.1:3000/api/tunnels | jq

# Start service
curl -X POST http://127.0.0.1:3000/api/start | jq

# Check running status
curl -s http://127.0.0.1:3000/api/status | jq

# Reload config (after editing tunnels.yaml)
curl -X POST http://127.0.0.1:3000/api/reload | jq

# Stop service
curl -X POST http://127.0.0.1:3000/api/stop | jq
```

---

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/config` | GET | Configuration info |
| `/api/tunnels` | GET | List all tunnels |
| `/api/status` | GET | Service status |
| `/api/start` | POST | Start frpc |
| `/api/stop` | POST | Stop frpc |
| `/api/restart` | POST | Restart frpc |
| `/api/reload` | POST | Reload YAML config |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Usage](../usage/) | [Documentation Index](../) | [Examples](../examples/) |

---

[Back to Index](../) | [Usage](../usage/) | [Examples](../examples/) | [Troubleshooting](../troubleshooting/)

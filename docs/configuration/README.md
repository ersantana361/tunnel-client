# Configuration Guide

This guide covers everything about configuring Tunnel Client using the YAML configuration file.

---

## Table of Contents

- [Config File Location](#config-file-location)
- [Config File Format](#config-file-format)
- [Server Settings](#server-settings)
- [Tunnel Types](#tunnel-types)
  - [HTTP Tunnels](#http-tunnels)
  - [HTTPS Tunnels](#https-tunnels)
  - [TCP Tunnels](#tcp-tunnels)
  - [UDP Tunnels](#udp-tunnels)
- [Tunnel Properties](#tunnel-properties)
- [Complete Reference](#complete-reference)
- [Validation Rules](#validation-rules)
- [Hot Reloading](#hot-reloading)

---

## Config File Location

The configuration file is located at:

```
./tunnels.yaml
```

This is relative to where you run `python3 app.py`.

### Getting Started

```bash
# Copy the example config
cp tunnels.example.yaml tunnels.yaml

# Edit with your settings
nano tunnels.yaml
```

---

## Config File Format

The configuration file uses YAML format with two main sections:

```yaml
# Server connection settings
server:
  url: "your-server.com:7000"
  token: "your-token-here"

# Tunnel definitions
tunnels:
  - name: tunnel-1
    type: http
    local_port: 8080
    subdomain: app

  - name: tunnel-2
    type: tcp
    local_port: 5432
    remote_port: 15432
```

---

## Server Settings

The `server` section configures how to connect to your tunnel server.

```yaml
server:
  url: "your-server.com:7000"    # Required: Server address and port
  token: "your-token-here"        # Required: Authentication token
```

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `url` | string | Yes | Server address in format `host:port` |
| `token` | string | Yes | Authentication token from server admin |

### URL Format

The URL should be in the format `host:port`:

```yaml
# Correct formats
url: "192.168.1.100:7000"
url: "tunnel.example.com:7000"
url: "my-server.com:7000"

# Incorrect formats (don't include protocol)
url: "http://my-server.com:7000"   # Wrong - no http://
url: "my-server.com"                # Wrong - missing port
```

### Token

Get your token from your tunnel server administrator. It's typically a long string:

```yaml
token: "abc123def456ghi789..."
```

> **Security Note**: Never commit `tunnels.yaml` to version control. Add it to `.gitignore`.

---

## Tunnel Types

### HTTP Tunnels

Expose web applications with subdomain-based routing.

```yaml
tunnels:
  - name: my-webapp
    description: "My web application"
    type: http
    local_port: 8080
    subdomain: myapp
```

**Access URL**: `http://myapp.your-server.com`

#### When to Use HTTP
- Web applications (React, Vue, Angular)
- REST APIs
- Static websites
- Development servers

#### HTTP Properties

| Property | Required | Description |
|----------|----------|-------------|
| `subdomain` | Yes | The subdomain prefix for routing |

---

### HTTPS Tunnels

Same as HTTP but for secure connections.

```yaml
tunnels:
  - name: secure-api
    description: "Secure API endpoint"
    type: https
    local_port: 443
    subdomain: api
```

**Access URL**: `https://api.your-server.com`

#### When to Use HTTPS
- APIs requiring SSL/TLS
- Secure web applications
- Production-like environments

---

### TCP Tunnels

Expose any TCP service with port mapping.

```yaml
tunnels:
  - name: postgres
    description: "PostgreSQL database"
    type: tcp
    local_port: 5432
    remote_port: 15432
```

**Access**: `your-server.com:15432`

#### When to Use TCP
- Databases (PostgreSQL, MySQL, MongoDB)
- SSH servers
- Custom TCP protocols
- Game servers

#### TCP Properties

| Property | Required | Description |
|----------|----------|-------------|
| `remote_port` | Yes | The port exposed on the server |

#### Common TCP Ports

| Service | Local Port | Suggested Remote Port |
|---------|------------|----------------------|
| PostgreSQL | 5432 | 15432 |
| MySQL | 3306 | 13306 |
| MongoDB | 27017 | 27017 |
| Redis | 6379 | 16379 |
| SSH | 22 | 2222 |

---

### UDP Tunnels

Expose UDP services.

```yaml
tunnels:
  - name: dns-server
    description: "DNS server"
    type: udp
    local_port: 53
    remote_port: 5353
```

**Access**: `your-server.com:5353` (UDP)

#### When to Use UDP
- DNS servers
- Game servers (real-time)
- VoIP applications
- Streaming services

---

## Tunnel Properties

### Complete Property Reference

| Property | Type | Required | For Types | Description |
|----------|------|----------|-----------|-------------|
| `name` | string | Yes | All | Unique identifier (alphanumeric, `-`, `_`) |
| `description` | string | No | All | Human-readable description |
| `type` | string | Yes | All | `http`, `https`, `tcp`, or `udp` |
| `local_port` | integer | Yes | All | Port on your local machine (1-65535) |
| `subdomain` | string | Yes* | http, https | Subdomain prefix for routing |
| `remote_port` | integer | Yes* | tcp, udp | Port exposed on the server (1-65535) |

*Required for the specified tunnel types.

### Name Rules

The tunnel name must:
- Start with a letter or number
- Contain only: `a-z`, `A-Z`, `0-9`, `-`, `_`
- Be 1-50 characters long
- Be unique across all tunnels

```yaml
# Valid names
name: my-api
name: web_server
name: app123
name: MyApp

# Invalid names
name: my api      # No spaces
name: @special!   # No special chars
name: ""          # Not empty
```

### Subdomain Rules

For HTTP/HTTPS tunnels, the subdomain must:
- Start with a letter or number
- Contain only: `a-z`, `0-9`, `-`
- Not start or end with `-`
- Be DNS-safe

```yaml
# Valid subdomains
subdomain: api
subdomain: my-app
subdomain: staging2

# Invalid subdomains
subdomain: -api       # Can't start with -
subdomain: my_app     # No underscores
subdomain: MY-APP     # Use lowercase
```

---

## Complete Reference

### Full Example Configuration

```yaml
# Tunnel Client Configuration
# Documentation: docs/configuration/

# Server connection
server:
  url: "tunnel.example.com:7000"
  token: "abc123def456ghi789jkl012mno345pqr678stu901vwx234"

# Tunnel definitions
tunnels:
  # HTTP: Web application
  - name: frontend
    description: "React frontend application"
    type: http
    local_port: 3000
    subdomain: app

  # HTTP: REST API
  - name: api
    description: "FastAPI backend"
    type: http
    local_port: 8000
    subdomain: api

  # HTTP: Documentation
  - name: docs
    description: "API documentation"
    type: http
    local_port: 8080
    subdomain: docs

  # TCP: PostgreSQL
  - name: postgres
    description: "PostgreSQL database"
    type: tcp
    local_port: 5432
    remote_port: 15432

  # TCP: Redis
  - name: redis
    description: "Redis cache"
    type: tcp
    local_port: 6379
    remote_port: 16379

  # TCP: SSH
  - name: ssh
    description: "SSH server"
    type: tcp
    local_port: 22
    remote_port: 2222
```

---

## Validation Rules

The application validates your configuration on load:

### Server Validation
- `url` must not be empty
- `token` must not be empty

### Tunnel Validation

| Rule | Error Message |
|------|---------------|
| Name empty | "name is required" |
| Name too long | "name must be 50 chars or less" |
| Name invalid chars | "name must be alphanumeric" |
| Duplicate name | "tunnel name already exists" |
| Invalid type | "type must be http, https, tcp, or udp" |
| Port out of range | "port must be between 1 and 65535" |
| HTTP missing subdomain | "subdomain required for HTTP tunnels" |
| TCP missing remote_port | "remote_port required for TCP tunnels" |

---

## Hot Reloading

You can update the configuration without restarting the application:

### Via Web UI

1. Edit `tunnels.yaml`
2. Open http://127.0.0.1:3000
3. Click **"Reload Config"**

### Via API

```bash
curl -X POST http://127.0.0.1:3000/api/reload
```

Response:
```json
{"message": "Configuration reloaded", "tunnel_count": 5}
```

### What Happens on Reload

1. YAML file is re-parsed
2. frpc.ini is regenerated
3. If frpc is running, it's automatically restarted
4. New tunnels become active

---

## Environment-Specific Configs

You can maintain different configs for different environments:

```bash
# Development
cp tunnels.yaml tunnels.dev.yaml

# Staging
cp tunnels.yaml tunnels.staging.yaml

# Switch environments (rename files)
mv tunnels.yaml tunnels.prod.yaml
mv tunnels.dev.yaml tunnels.yaml
```

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Getting Started](../getting-started/) | [Documentation Index](../) | [Usage](../usage/) |

---

[Back to Index](../) | [Getting Started](../getting-started/) | [Usage](../usage/) | [Examples](../examples/)

# Tunnel Client Documentation

Web-based client for managing FRP tunnels.

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](./getting-started/) | Installation and first steps |
| [Configuration](./configuration/) | Environment variables and tunnel settings |
| [Usage](./usage/) | Web UI and API usage |
| [API Reference](./api/) | REST API endpoints |
| [Architecture](./architecture/) | How it works internally |
| [Troubleshooting](./troubleshooting/) | Common issues and solutions |

---

## Overview

Tunnel Client provides a web interface for managing [FRP (Fast Reverse Proxy)](https://github.com/fatedier/frp) tunnels. It runs as two Docker containers:

- **tunnel-client** - Web UI and API server
- **frpc** - Tunnel proxy (always running)

### Key Features

- **Web Dashboard** - Create, edit, delete tunnels at http://localhost:3002
- **Server Authentication** - Login with your tunnel server credentials
- **Hot Reload** - Config changes apply instantly via frpc admin API
- **Docker Native** - Two-container architecture with auto-restart
- **Export/Import** - Backup and restore tunnel configurations

---

## Quick Start

```bash
# Set token
export TUNNEL_TOKEN="your-token"

# Start containers
docker compose up -d

# Open browser
open http://localhost:3002
```

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

## Documentation Structure

```
docs/
├── README.md              # This file
├── getting-started/       # Installation guide
├── configuration/         # Environment and tunnel settings
├── usage/                 # Web UI and API usage
├── api/                   # REST API reference
├── architecture/          # Internal design
└── troubleshooting/       # Common issues
```

---

[Back to Project](../) | [Getting Started](./getting-started/)

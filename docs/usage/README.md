# Usage Guide

This guide covers how to use Tunnel Client on a daily basis, including the web UI, CLI options, and service management.

---

## Table of Contents

- [Web UI](#web-ui)
  - [Dashboard Overview](#dashboard-overview)
  - [Service Controls](#service-controls)
  - [Tunnel List](#tunnel-list)
  - [Reloading Configuration](#reloading-configuration)
- [CLI Options](#cli-options)
- [Managing Tunnels](#managing-tunnels)
- [Running as a Service](#running-as-a-service)
- [Logs and Monitoring](#logs-and-monitoring)

---

## Web UI

The web UI provides a real-time dashboard for monitoring and controlling your tunnels.

### Accessing the UI

Start the application and open your browser:

```bash
python3 app.py
# Open: http://127.0.0.1:3000
```

### Dashboard Overview

The dashboard displays:

```
┌─────────────────────────────────────────────────────────┐
│  Tunnel Client                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ● Connected (PID: 12345)                              │
│                                                         │
│  [Start]  [Stop]  [Restart]  [Reload Config]           │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Tunnels (3)                                            │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ my-api                                    HTTP  │   │
│  │ localhost:8080 -> api.[server]                  │   │
│  │ REST API backend                                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ frontend                                  HTTP  │   │
│  │ localhost:3000 -> app.[server]                  │   │
│  │ React frontend                                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ postgres                                   TCP  │   │
│  │ localhost:5432 -> [server]:15432                │   │
│  │ PostgreSQL database                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Config file: tunnels.yaml                             │
│  Edit the config file to add or remove tunnels         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Status Indicator

| Status | Indicator | Description |
|--------|-----------|-------------|
| Connected | Green dot | frpc is running and connected |
| Disconnected | Red dot | frpc is not running |

---

### Service Controls

#### Start Button
Starts the frpc service to establish tunnels.

```
[Start] → Starts frpc → Tunnels become active
```

#### Stop Button
Stops the frpc service and closes all tunnels.

```
[Stop] → Stops frpc → Tunnels become inactive
```

#### Restart Button
Restarts the frpc service (useful after config changes).

```
[Restart] → Stop → Start → Tunnels reconnect
```

#### Reload Config Button
Reloads the YAML configuration file without restarting the app.

```
[Reload Config] → Re-reads tunnels.yaml → Updates tunnel list
```

If frpc is running, it will be automatically restarted to apply changes.

---

### Tunnel List

The tunnel list shows all tunnels defined in `tunnels.yaml`:

| Element | Description |
|---------|-------------|
| **Name** | Tunnel identifier (e.g., `my-api`) |
| **Type Badge** | HTTP, HTTPS, TCP, or UDP |
| **Routing** | Local port and where it's exposed |
| **Description** | Optional description from config |

---

### Reloading Configuration

When you modify `tunnels.yaml`:

1. **Edit the file**:
   ```bash
   nano tunnels.yaml
   ```

2. **Click "Reload Config"** in the web UI

3. **Verify changes** in the tunnel list

Alternatively, use the API:
```bash
curl -X POST http://127.0.0.1:3000/api/reload
```

---

## CLI Options

### Basic Usage

```bash
python3 app.py [options]
```

### Available Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `127.0.0.1` | Host/IP to bind to |
| `--port` | `3000` | Port to listen on |
| `--help` | - | Show help message |

### Examples

```bash
# Default: localhost:3000
python3 app.py

# Custom port
python3 app.py --port 3001

# Listen on all interfaces (for network access)
python3 app.py --host 0.0.0.0

# Both options
python3 app.py --host 0.0.0.0 --port 8080

# Show help
python3 app.py --help
```

### Security Note

Using `--host 0.0.0.0` exposes the UI to your network. Only use this on trusted networks.

---

## Managing Tunnels

### Adding a Tunnel

1. Open `tunnels.yaml` in your editor
2. Add a new tunnel entry:
   ```yaml
   tunnels:
     # ... existing tunnels ...

     - name: new-tunnel
       description: "My new service"
       type: http
       local_port: 9000
       subdomain: newapp
   ```
3. Save the file
4. Click "Reload Config" in the UI

### Removing a Tunnel

1. Open `tunnels.yaml`
2. Delete or comment out the tunnel:
   ```yaml
   tunnels:
     # - name: old-tunnel
     #   type: http
     #   local_port: 8000
     #   subdomain: old
   ```
3. Save and reload

### Modifying a Tunnel

1. Edit the tunnel in `tunnels.yaml`
2. Save and reload

> **Note**: Tunnel names must be unique. To rename, delete the old entry and create a new one.

---

## Running as a Service

### Creating a Systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/tunnel-client.service
```

Add the following content:

```ini
[Unit]
Description=Tunnel Client
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/tunnel-client
ExecStart=/usr/bin/python3 /path/to/tunnel-client/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enabling the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable tunnel-client

# Start the service
sudo systemctl start tunnel-client
```

### Service Commands

| Command | Description |
|---------|-------------|
| `systemctl status tunnel-client` | Check service status |
| `sudo systemctl start tunnel-client` | Start the service |
| `sudo systemctl stop tunnel-client` | Stop the service |
| `sudo systemctl restart tunnel-client` | Restart the service |
| `journalctl -u tunnel-client -f` | Follow logs |

### Checking Service Status

```bash
systemctl status tunnel-client
```

Expected output:
```
● tunnel-client.service - Tunnel Client
     Loaded: loaded (/etc/systemd/system/tunnel-client.service; enabled)
     Active: active (running) since ...
     Main PID: 12345 (python3)
```

---

## Logs and Monitoring

### Application Logs

The application logs to stdout. View with:

```bash
# If running directly
python3 app.py  # Logs appear in terminal

# If running as service
journalctl -u tunnel-client -f
```

### frpc Logs

frpc subprocess logs are written to `/tmp/frpc.log`:

```bash
# View frpc logs
cat /tmp/frpc.log

# Follow in real-time
tail -f /tmp/frpc.log
```

### Log Levels

| Level | Example |
|-------|---------|
| INFO | `Loaded 3 tunnel(s) from tunnels.yaml` |
| INFO | `frpc started with PID 12345` |
| WARNING | `Config file not found` |
| ERROR | `Failed to start frpc` |

### Monitoring Endpoints

Use the API for programmatic monitoring:

```bash
# Check if frpc is running
curl http://127.0.0.1:3000/api/status
# {"running": true, "pid": 12345}

# Get tunnel count
curl http://127.0.0.1:3000/api/config
# {"configured": true, "tunnel_count": 3, ...}
```

---

## Quick Reference

### Start/Stop Workflow

```bash
# Start app
python3 app.py &

# Start tunnels (via API)
curl -X POST http://127.0.0.1:3000/api/start

# Check status
curl http://127.0.0.1:3000/api/status

# Reload after config change
curl -X POST http://127.0.0.1:3000/api/reload

# Stop tunnels
curl -X POST http://127.0.0.1:3000/api/stop
```

### Common Operations

| Task | How To |
|------|--------|
| Start tunnels | Click "Start" or `POST /api/start` |
| Stop tunnels | Click "Stop" or `POST /api/stop` |
| Add tunnel | Edit YAML, click "Reload Config" |
| Check status | Look at status indicator or `GET /api/status` |
| View logs | `tail -f /tmp/frpc.log` |

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Configuration](../configuration/) | [Documentation Index](../) | [API Reference](../api/) |

---

[Back to Index](../) | [Configuration](../configuration/) | [API Reference](../api/) | [Examples](../examples/)

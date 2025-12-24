# Getting Started

This guide will help you install and set up Tunnel Client for the first time.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Quick Install](#quick-install)
  - [Manual Install](#manual-install)
- [Quick Start](#quick-start)
- [Verifying Installation](#verifying-installation)
- [Next Steps](#next-steps)

---

## Prerequisites

Before installing Tunnel Client, ensure you have:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.8+ | `python3 --version` |
| pip | Any | `pip3 --version` |
| wget or curl | Any | `which wget curl` |
| sudo access | - | `sudo -v` |

You'll also need:
- **Server URL**: The address of your tunnel server (e.g., `your-server.com:7000`)
- **Token**: Authentication token from your server admin

---

## Installation

### Quick Install

The fastest way to get started:

```bash
# Clone or download the project
cd tunnel-client

# Run the installer
chmod +x install.sh
./install.sh
```

The installer will:
1. Install Python dependencies
2. Download and install the `frpc` binary
3. Create necessary directories
4. Set up a systemd service (optional)

### Manual Install

If you prefer manual installation:

#### Step 1: Install Python Dependencies

```bash
pip3 install -r requirements.txt --break-system-packages
```

Dependencies installed:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `pyyaml` - YAML parsing
- `requests` - HTTP client

#### Step 2: Install frpc Binary

```bash
# Download frp
FRP_VERSION="0.52.3"
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz

# Extract
tar -xzf frp_${FRP_VERSION}_linux_amd64.tar.gz

# Install frpc
sudo cp frp_${FRP_VERSION}_linux_amd64/frpc /usr/local/bin/
sudo chmod +x /usr/local/bin/frpc

# Verify
frpc --version
```

#### Step 3: Create Config Directory

```bash
sudo mkdir -p /etc/frp
sudo chown $USER:$USER /etc/frp
```

#### Step 4: Create Configuration File

```bash
cp tunnels.example.yaml tunnels.yaml
```

Edit `tunnels.yaml` with your server details:

```yaml
server:
  url: "your-server.com:7000"
  token: "your-token-here"

tunnels:
  - name: my-first-tunnel
    type: http
    local_port: 8080
    subdomain: myapp
```

> See [Configuration Guide](../configuration/) for detailed options.

---

## Quick Start

### 1. Create Your Configuration

```bash
cp tunnels.example.yaml tunnels.yaml
nano tunnels.yaml  # or your preferred editor
```

Minimal configuration:

```yaml
server:
  url: "your-server.com:7000"
  token: "your-token-here"

tunnels:
  - name: web
    type: http
    local_port: 8080
    subdomain: mysite
```

### 2. Start the Application

```bash
python3 app.py
```

You should see:

```
INFO - Loaded 1 tunnel(s) from tunnels.yaml
INFO - frpc found at /usr/local/bin/frpc
INFO - Uvicorn running on http://127.0.0.1:3000
```

### 3. Open the Web UI

Open your browser to: **http://127.0.0.1:3000**

You'll see:
- Your configured tunnels
- Connection status
- Start/Stop/Restart buttons

### 4. Start the Tunnel Service

Click the **Start** button in the web UI, or use the API:

```bash
curl -X POST http://127.0.0.1:3000/api/start
```

### 5. Test Your Tunnel

If you configured an HTTP tunnel with subdomain `mysite`:

```bash
# Start a local server
python3 -m http.server 8080

# Access via tunnel
curl http://mysite.your-server.com
```

---

## Verifying Installation

### Check Python Dependencies

```bash
pip3 show fastapi uvicorn pydantic pyyaml
```

### Check frpc Installation

```bash
which frpc
frpc --version
# Expected: frpc version 0.52.3
```

### Check Config Directory

```bash
ls -la /etc/frp/
# Should exist and be writable
```

### Test Application Startup

```bash
python3 app.py --help
```

Expected output:
```
usage: app.py [-h] [--host HOST] [--port PORT]

Tunnel Client - Web UI for managing FRP tunnels

options:
  -h, --help   show this help message and exit
  --host HOST  Host to bind to (default: 127.0.0.1)
  --port PORT  Port to listen on (default: 3000)
```

---

## Next Steps

Now that you have Tunnel Client installed:

1. **[Configure Your Tunnels](../configuration/)** - Learn about tunnel types and options
2. **[Explore the Web UI](../usage/#web-ui)** - Monitor and control your tunnels
3. **[See Examples](../examples/)** - Common use cases and recipes
4. **[Run as a Service](../usage/#running-as-a-service)** - Auto-start on boot

---

## Common Installation Issues

| Issue | Solution |
|-------|----------|
| `pip3: command not found` | Install Python: `sudo apt install python3-pip` |
| `Permission denied` on frpc | Run: `sudo chmod +x /usr/local/bin/frpc` |
| `externally-managed-environment` | Add `--break-system-packages` to pip |
| Port 3000 in use | Use `--port 3001` or stop the other service |

> See [Troubleshooting](../troubleshooting/) for more solutions.

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| - | [Documentation Index](../) | [Configuration](../configuration/) |

---

[Back to Index](../) | [Configuration](../configuration/) | [Usage](../usage/) | [Examples](../examples/)

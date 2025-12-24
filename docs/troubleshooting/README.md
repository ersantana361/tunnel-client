# Troubleshooting Guide

This guide helps you diagnose and fix common issues with Tunnel Client.

---

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Connection Issues](#connection-issues)
- [Service Issues](#service-issues)
- [Tunnel Issues](#tunnel-issues)
- [Web UI Issues](#web-ui-issues)
- [Logs and Debugging](#logs-and-debugging)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

Run these commands to quickly identify issues:

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check frpc installation
which frpc
frpc --version  # Should be 0.52.3

# Check if app is running
curl -s http://127.0.0.1:3000/api/status

# Check frpc logs
tail -20 /tmp/frpc.log

# Check config file
cat tunnels.yaml
```

---

## Installation Issues

### "pip3: command not found"

**Problem**: pip is not installed.

**Solution**:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip

# Fedora
sudo dnf install python3-pip

# macOS
python3 -m ensurepip --upgrade
```

---

### "externally-managed-environment" Error

**Problem**: Python is managed by the system package manager.

**Solution**: Add the `--break-system-packages` flag:

```bash
pip3 install -r requirements.txt --break-system-packages
```

Or use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### "frpc: command not found"

**Problem**: frpc binary not installed or not in PATH.

**Solution**:

```bash
# Check if installed
ls -la /usr/local/bin/frpc

# If not found, install it
FRP_VERSION="0.52.3"
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz
tar -xzf frp_${FRP_VERSION}_linux_amd64.tar.gz
sudo cp frp_${FRP_VERSION}_linux_amd64/frpc /usr/local/bin/
sudo chmod +x /usr/local/bin/frpc
```

---

### "Permission denied" on frpc

**Problem**: frpc binary doesn't have execute permission.

**Solution**:

```bash
sudo chmod +x /usr/local/bin/frpc
```

---

## Configuration Issues

### "No Configuration Found" in Web UI

**Problem**: `tunnels.yaml` file doesn't exist or isn't readable.

**Solution**:

```bash
# Check if file exists
ls -la tunnels.yaml

# Create from example
cp tunnels.example.yaml tunnels.yaml

# Verify it's valid YAML
python3 -c "import yaml; yaml.safe_load(open('tunnels.yaml'))"
```

---

### "Failed to reload config"

**Problem**: YAML syntax error or missing required fields.

**Solution**:

1. Validate YAML syntax:
   ```bash
   python3 -c "import yaml; print(yaml.safe_load(open('tunnels.yaml')))"
   ```

2. Check for common issues:
   - Missing colons after keys
   - Incorrect indentation (use spaces, not tabs)
   - Missing quotes around values with special characters

3. Example of correct YAML:
   ```yaml
   server:
     url: "server.com:7000"    # Quotes recommended
     token: "my-token"

   tunnels:
     - name: my-tunnel         # Dash + space for list items
       type: http
       local_port: 8080        # Numbers without quotes
       subdomain: app
   ```

---

### "Server URL or token not configured"

**Problem**: Server settings missing from config.

**Solution**:

Check your `tunnels.yaml`:

```yaml
server:
  url: "your-server.com:7000"    # Must not be empty
  token: "your-token-here"       # Must not be empty

tunnels:
  # ...
```

---

## Connection Issues

### "Connection refused" to Server

**Problem**: Can't connect to the tunnel server.

**Diagnosis**:

```bash
# Test connectivity
telnet your-server.com 7000
# or
nc -zv your-server.com 7000
```

**Solutions**:

1. **Wrong port**: Use the frp port (usually 7000), not the admin port (8000)
   ```yaml
   # Correct
   url: "server.com:7000"

   # Wrong (admin port)
   url: "server.com:8000"
   ```

2. **Firewall blocking**: Check server firewall allows port 7000

3. **Server not running**: Contact your server administrator

---

### "Login failed" or "Token error"

**Problem**: Authentication with server failed.

**Solutions**:

1. **Check token**: Ensure token matches exactly (no extra spaces)
   ```yaml
   token: "abc123"    # Correct
   token: " abc123"   # Wrong (leading space)
   token: "abc123 "   # Wrong (trailing space)
   ```

2. **Get new token**: Contact your server admin for a fresh token

3. **Check server logs** on the server side

---

### "Subdomain already in use"

**Problem**: Another client is using the same subdomain.

**Solutions**:

1. Choose a different subdomain:
   ```yaml
   subdomain: my-unique-app-name
   ```

2. Check if you have another instance running

---

## Service Issues

### "Service won't start"

**Problem**: frpc fails to start.

**Diagnosis**:

```bash
# Check logs
cat /tmp/frpc.log

# Try running frpc manually
frpc -c /etc/frp/frpc.ini
```

**Common causes**:

| Log Message | Solution |
|-------------|----------|
| "config file not found" | Run reload first: `curl -X POST .../api/reload` |
| "connection refused" | Check server URL and port |
| "token invalid" | Check token in config |
| "subdomain in use" | Choose different subdomain |

---

### "Already running" Error

**Problem**: Trying to start when already running.

**Solution**:

```bash
# Check status
curl http://127.0.0.1:3000/api/status

# Stop first, then start
curl -X POST http://127.0.0.1:3000/api/stop
curl -X POST http://127.0.0.1:3000/api/start
```

---

### "Not running" Error

**Problem**: Trying to stop when not running.

**Solution**: This is expected if frpc isn't running. Just start it:

```bash
curl -X POST http://127.0.0.1:3000/api/start
```

---

### Stale PID File

**Problem**: PID file exists but process is dead.

**Solution**: The app auto-cleans stale PID files, but you can manually remove:

```bash
rm /tmp/frpc.pid
```

---

## Tunnel Issues

### Tunnel Not Working

**Diagnosis checklist**:

1. **Is frpc running?**
   ```bash
   curl http://127.0.0.1:3000/api/status
   ```

2. **Is local service running?**
   ```bash
   curl localhost:8080  # Replace with your port
   ```

3. **Check frpc logs**:
   ```bash
   cat /tmp/frpc.log
   ```

4. **Is tunnel in config?**
   ```bash
   curl http://127.0.0.1:3000/api/tunnels
   ```

---

### "Proxy not found"

**Problem**: Tunnel name doesn't exist in config.

**Solution**: Verify tunnel is defined in `tunnels.yaml` and reload:

```bash
curl -X POST http://127.0.0.1:3000/api/reload
```

---

### Tunnel Works Locally but Not Remotely

**Problem**: Can access `localhost:8080` but not `app.server.com`.

**Possible causes**:

1. **DNS not propagated**: Wait or try IP directly
2. **Server firewall**: Check HTTP port (usually 80 or 8080) is open
3. **Server config**: Ensure `subdomain_host` is configured on server

---

## Web UI Issues

### "Cannot connect to http://127.0.0.1:3000"

**Problem**: App not running or wrong port.

**Solutions**:

1. **Start the app**:
   ```bash
   python3 app.py
   ```

2. **Check which port**:
   ```bash
   python3 app.py --port 3001  # If 3000 is in use
   ```

3. **Check if something else is using the port**:
   ```bash
   lsof -i :3000
   ```

---

### "Port already in use"

**Problem**: Another process is using port 3000.

**Solutions**:

1. **Use different port**:
   ```bash
   python3 app.py --port 3001
   ```

2. **Find and kill the process**:
   ```bash
   lsof -i :3000
   kill <PID>
   ```

---

### UI Shows "No tunnels" but They're Configured

**Problem**: Config not loaded or reload needed.

**Solution**:

```bash
# Click "Reload Config" in UI
# or
curl -X POST http://127.0.0.1:3000/api/reload
```

---

## Logs and Debugging

### Application Logs

```bash
# Running directly
python3 app.py  # Logs appear in terminal

# Running as service
journalctl -u tunnel-client -f
```

### frpc Logs

```bash
# View all logs
cat /tmp/frpc.log

# Follow in real-time
tail -f /tmp/frpc.log

# Search for errors
grep -i error /tmp/frpc.log
grep -i warning /tmp/frpc.log
```

### Log Locations

| Log | Location |
|-----|----------|
| Application | stdout (terminal) or journalctl |
| frpc | `/tmp/frpc.log` |
| frpc PID | `/tmp/frpc.pid` |
| frpc config | `/etc/frp/frpc.ini` |

### Debug Mode

For more verbose output:

```bash
# Set log level
LOG_LEVEL=DEBUG python3 app.py
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Missing tunnels.yaml | Create config file |
| "Failed to parse YAML" | Syntax error | Check YAML formatting |
| "Connection refused" | Server unreachable | Check URL and firewall |
| "Token invalid" | Wrong token | Verify token |
| "Subdomain in use" | Conflict | Use different subdomain |
| "Port already in use" | Conflict | Use different port |
| "Permission denied" | File permissions | Check file ownership |

---

## Getting Help

If you can't resolve your issue:

1. **Gather information**:
   ```bash
   python3 --version
   frpc --version
   cat tunnels.yaml
   cat /tmp/frpc.log
   curl http://127.0.0.1:3000/api/status
   ```

2. **Check documentation**:
   - [Getting Started](../getting-started/)
   - [Configuration](../configuration/)
   - [Examples](../examples/)

3. **Open an issue** with:
   - Error message
   - Config (redact token)
   - frpc log output
   - Steps to reproduce

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [Examples](../examples/) | [Documentation Index](../) | [Architecture](../architecture/) |

---

[Back to Index](../) | [Examples](../examples/) | [Architecture](../architecture/) | [Getting Started](../getting-started/)

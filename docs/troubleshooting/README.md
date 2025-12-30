# Troubleshooting

Common issues and solutions for the Docker-based setup.

---

## Quick Diagnostics

```bash
# Check containers are running
docker compose ps

# Check frpc logs
docker compose logs -f frpc

# Check tunnel-client logs
docker compose logs -f tunnel-client

# Check frpc status via API
curl http://localhost:3002/api/status
```

---

## Token Mismatch

**Error**: `token in login doesn't match token from configuration`

**Cause**: TUNNEL_TOKEN environment variable doesn't match server token.

**Solution**:
```bash
# Update token in your env file
export TUNNEL_TOKEN="new-token-here"

# Restart frpc container
docker compose restart frpc
```

---

## frpc Not Connecting

**Symptoms**: frpc logs show "connection refused" or timeout

**Check logs**:
```bash
docker compose logs -f frpc
```

**Solutions**:

1. **Verify server URL** - Check the server is reachable
2. **Check firewall** - Ensure port 7000 is open
3. **Check token** - Update TUNNEL_TOKEN if needed

---

## Container Won't Start

**Check logs**:
```bash
docker compose logs tunnel-client
docker compose logs frpc
```

**Rebuild**:
```bash
docker compose build --no-cache && docker compose up -d
```

---

## Web UI Not Loading

**Check container status**:
```bash
docker compose ps
```

**Check if accessible**:
```bash
curl http://localhost:3002/api/status
```

**Restart**:
```bash
docker compose restart tunnel-client
```

---

## Tunnel Not Working

### Check frpc status
```bash
curl http://localhost:3002/api/status
```

### Check if local service is running
```bash
curl http://localhost:8080  # your local port
```

### For Docker services, check local_host setting

| Scenario | local_host Value |
|----------|------------------|
| Host machine service | `host.docker.internal` |
| Container on same network | Container name |

Update via API:
```bash
curl -X PUT http://localhost:3002/api/tunnels/1 \
  -H 'Content-Type: application/json' \
  -d '{"name":"myapp","local_host":"host.docker.internal",...}'
```

---

## Config Not Reloading

**Force reload**:
```bash
curl -X POST http://localhost:3002/api/restart
```

**Check frpc admin API is reachable**:
```bash
docker exec tunnel-client curl http://frpc:7400/api/status
```

---

## Container Can't Reach Other Containers

**Problem**: Tunnels show "connection refused" for other Docker services.

**Cause**: frpc container not on the same network.

**Solution**:
```bash
# Connect frpc to target network
docker network connect <network-name> frpc

# Reload config
curl -X POST http://localhost:3002/api/restart
```

---

## Viewing Logs

**All containers**:
```bash
docker compose logs -f
```

**frpc only**:
```bash
docker compose logs -f frpc
```

**tunnel-client only**:
```bash
docker compose logs -f tunnel-client
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `token mismatch` | Wrong TUNNEL_TOKEN | Update token, restart frpc |
| `connection refused` | Server unreachable | Check server URL and firewall |
| `frpc not reachable` | frpc container not running | `docker compose up -d` |
| `401 Unauthorized` | Invalid login credentials | Re-login in web UI |
| `subdomain in use` | Conflict with another user | Choose different subdomain |

---

## Getting Help

1. **Gather logs**:
   ```bash
   docker compose logs > logs.txt
   ```

2. **Check status**:
   ```bash
   curl http://localhost:3002/api/status
   ```

3. Review [Architecture](../architecture/) to understand the system

---

[Back to Documentation](../)

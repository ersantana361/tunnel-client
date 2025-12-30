# Examples & Recipes

Common tunnel configurations and use cases.

---

## Web Development

### HTTP Tunnel for Web App

Expose a local web server.

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "webapp",
    "type": "http",
    "local_port": 8080,
    "local_host": "host.docker.internal",
    "subdomain": "myapp"
  }'
```

**Access**: `http://myapp.your-server.com`

### React/Vue/Angular Dev Server

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "frontend",
    "type": "http",
    "local_port": 3000,
    "local_host": "host.docker.internal",
    "subdomain": "app"
  }'
```

---

## API Development

### REST API

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "api",
    "type": "http",
    "local_port": 8000,
    "local_host": "host.docker.internal",
    "subdomain": "api"
  }'
```

**Test**:
```bash
curl http://api.your-server.com/health
```

### Webhook Testing

Expose your local server for webhook callbacks:

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "webhooks",
    "type": "http",
    "local_port": 5000,
    "local_host": "host.docker.internal",
    "subdomain": "webhooks"
  }'
```

---

## Database Access

### PostgreSQL

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "postgres",
    "type": "tcp",
    "local_port": 5432,
    "local_host": "host.docker.internal",
    "remote_port": 15432
  }'
```

**Connect**:
```bash
psql -h your-server.com -p 15432 -U postgres
```

### MySQL

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "mysql",
    "type": "tcp",
    "local_port": 3306,
    "local_host": "host.docker.internal",
    "remote_port": 13306
  }'
```

### Redis

```bash
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "redis",
    "type": "tcp",
    "local_port": 6379,
    "local_host": "host.docker.internal",
    "remote_port": 16379
  }'
```

---

## Docker Container Tunnels

### Tunnel to Another Container

1. Connect frpc to the container's network:
   ```bash
   docker network connect myapp_default frpc
   ```

2. Create tunnel using container name:
   ```bash
   curl -X POST http://localhost:3002/api/tunnels \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "flask-app",
       "type": "http",
       "local_port": 5000,
       "local_host": "flask-container",
       "subdomain": "flask"
     }'
   ```

3. Reload:
   ```bash
   curl -X POST http://localhost:3002/api/restart
   ```

---

## Full-Stack Setup

Create multiple tunnels for a full stack:

```bash
# Frontend
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{"name":"frontend","type":"http","local_port":3000,"local_host":"host.docker.internal","subdomain":"app"}'

# Backend API
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{"name":"api","type":"http","local_port":8000,"local_host":"host.docker.internal","subdomain":"api"}'

# Database
curl -X POST http://localhost:3002/api/tunnels \
  -H 'Content-Type: application/json' \
  -d '{"name":"postgres","type":"tcp","local_port":5432,"local_host":"host.docker.internal","remote_port":15432}'

# Reload to apply all
curl -X POST http://localhost:3002/api/restart
```

---

## Export/Import

### Backup Tunnels

```bash
curl http://localhost:3002/api/tunnels/export > tunnels-backup.json
```

### Restore Tunnels

```bash
curl -X POST http://localhost:3002/api/tunnels/import \
  -H 'Content-Type: application/json' \
  -d @tunnels-backup.json
```

---

## Tips

### local_host Values

| Scenario | local_host |
|----------|------------|
| Host machine | `host.docker.internal` |
| Same network container | Container name |
| Default (in container) | `127.0.0.1` |

### Common Ports

| Service | Local | Suggested Remote |
|---------|-------|------------------|
| PostgreSQL | 5432 | 15432 |
| MySQL | 3306 | 13306 |
| MongoDB | 27017 | 27017 |
| Redis | 6379 | 16379 |
| SSH | 22 | 2222 |

---

[Back to Documentation](../)

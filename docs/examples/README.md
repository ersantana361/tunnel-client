# Examples & Recipes

This guide provides common use cases and ready-to-use configurations for various scenarios.

---

## Table of Contents

- [Web Development](#web-development)
  - [Example 1: Expose a Web Server](#example-1-expose-a-web-server)
  - [Example 2: React/Vue/Angular App](#example-2-reactvueangular-app)
  - [Example 3: Full-Stack Development](#example-3-full-stack-development)
- [API Development](#api-development)
  - [Example 4: REST API](#example-4-rest-api)
  - [Example 5: GraphQL Server](#example-5-graphql-server)
- [Database Access](#database-access)
  - [Example 6: PostgreSQL](#example-6-postgresql)
  - [Example 7: MySQL](#example-7-mysql)
  - [Example 8: MongoDB](#example-8-mongodb)
  - [Example 9: Redis](#example-9-redis)
- [DevOps & Infrastructure](#devops--infrastructure)
  - [Example 10: SSH Access](#example-10-ssh-access)
  - [Example 11: Docker Registry](#example-11-docker-registry)
- [Complete Configurations](#complete-configurations)
  - [Microservices Setup](#microservices-setup)
  - [Development Environment](#development-environment)

---

## Web Development

### Example 1: Expose a Web Server

Expose a simple HTTP server to the internet.

**Use Case**: Share a local website with a client or test webhooks.

**Configuration**:

```yaml
server:
  url: "your-server.com:7000"
  token: "your-token"

tunnels:
  - name: website
    description: "My local website"
    type: http
    local_port: 8080
    subdomain: mysite
```

**Start a test server**:

```bash
# Python HTTP server
python3 -m http.server 8080

# Or with Node.js
npx serve -l 8080
```

**Access**: `http://mysite.your-server.com`

---

### Example 2: React/Vue/Angular App

Expose a frontend development server.

**Use Case**: Demo to stakeholders, test on mobile devices.

**Configuration**:

```yaml
tunnels:
  - name: frontend
    description: "React development server"
    type: http
    local_port: 3000
    subdomain: app
```

**Start your dev server**:

```bash
# React
npm start  # Runs on :3000

# Vue
npm run serve  # Runs on :8080

# Angular
ng serve  # Runs on :4200
```

> Adjust `local_port` to match your framework's default.

**Access**: `http://app.your-server.com`

---

### Example 3: Full-Stack Development

Expose both frontend and backend simultaneously.

**Use Case**: Full-stack development with separate servers.

**Configuration**:

```yaml
tunnels:
  - name: frontend
    description: "React frontend"
    type: http
    local_port: 3000
    subdomain: app

  - name: backend
    description: "Express API"
    type: http
    local_port: 5000
    subdomain: api
```

**Start both servers**:

```bash
# Terminal 1: Frontend
cd frontend && npm start

# Terminal 2: Backend
cd backend && npm run dev
```

**Access**:
- Frontend: `http://app.your-server.com`
- Backend: `http://api.your-server.com`

---

## API Development

### Example 4: REST API

Expose a REST API for testing or integration.

**Use Case**: Webhook testing, mobile app development, third-party integration.

**Configuration**:

```yaml
tunnels:
  - name: api
    description: "REST API"
    type: http
    local_port: 8000
    subdomain: api
```

**Framework examples**:

```bash
# FastAPI
uvicorn main:app --port 8000

# Flask
flask run --port 8000

# Express
node server.js  # Configure to use port 8000

# Django
python manage.py runserver 8000

# Spring Boot
./mvnw spring-boot:run  # Default: 8080
```

**Access**: `http://api.your-server.com`

**Test with curl**:

```bash
curl http://api.your-server.com/health
curl -X POST http://api.your-server.com/users -d '{"name": "test"}'
```

---

### Example 5: GraphQL Server

Expose a GraphQL endpoint.

**Use Case**: GraphQL development, GraphQL playground access.

**Configuration**:

```yaml
tunnels:
  - name: graphql
    description: "GraphQL API"
    type: http
    local_port: 4000
    subdomain: graphql
```

**Start your server**:

```bash
# Apollo Server
node server.js  # Default: 4000

# Hasura
docker run -p 4000:8080 hasura/graphql-engine
```

**Access**:
- Endpoint: `http://graphql.your-server.com/graphql`
- Playground: `http://graphql.your-server.com/graphql`

---

## Database Access

### Example 6: PostgreSQL

Expose PostgreSQL for remote access.

**Use Case**: Team database access, remote development.

**Configuration**:

```yaml
tunnels:
  - name: postgres
    description: "PostgreSQL database"
    type: tcp
    local_port: 5432
    remote_port: 15432
```

**Connect remotely**:

```bash
# psql
psql -h your-server.com -p 15432 -U postgres -d mydb

# Connection string
postgresql://postgres:password@your-server.com:15432/mydb
```

**GUI clients** (DBeaver, pgAdmin, TablePlus):
- Host: `your-server.com`
- Port: `15432`
- User: `postgres`

---

### Example 7: MySQL

Expose MySQL for remote access.

**Configuration**:

```yaml
tunnels:
  - name: mysql
    description: "MySQL database"
    type: tcp
    local_port: 3306
    remote_port: 13306
```

**Connect remotely**:

```bash
# mysql cli
mysql -h your-server.com -P 13306 -u root -p

# Connection string
mysql://root:password@your-server.com:13306/mydb
```

---

### Example 8: MongoDB

Expose MongoDB for remote access.

**Configuration**:

```yaml
tunnels:
  - name: mongodb
    description: "MongoDB database"
    type: tcp
    local_port: 27017
    remote_port: 27017
```

**Connect remotely**:

```bash
# mongosh
mongosh "mongodb://your-server.com:27017"

# Connection string
mongodb://your-server.com:27017/mydb
```

---

### Example 9: Redis

Expose Redis for remote access.

**Configuration**:

```yaml
tunnels:
  - name: redis
    description: "Redis cache"
    type: tcp
    local_port: 6379
    remote_port: 16379
```

**Connect remotely**:

```bash
# redis-cli
redis-cli -h your-server.com -p 16379

# Connection string
redis://your-server.com:16379
```

---

## DevOps & Infrastructure

### Example 10: SSH Access

Expose SSH for remote server access.

**Configuration**:

```yaml
tunnels:
  - name: ssh
    description: "SSH server"
    type: tcp
    local_port: 22
    remote_port: 2222
```

**Connect remotely**:

```bash
ssh user@your-server.com -p 2222
```

**SSH config** (`~/.ssh/config`):

```
Host mytunnel
    HostName your-server.com
    Port 2222
    User your-username
```

Then: `ssh mytunnel`

---

### Example 11: Docker Registry

Expose a local Docker registry.

**Configuration**:

```yaml
tunnels:
  - name: registry
    description: "Docker registry"
    type: http
    local_port: 5000
    subdomain: registry
```

**Start registry**:

```bash
docker run -d -p 5000:5000 --name registry registry:2
```

**Use from anywhere**:

```bash
docker tag myimage registry.your-server.com/myimage
docker push registry.your-server.com/myimage
```

---

## Complete Configurations

### Microservices Setup

Full microservices development environment.

```yaml
server:
  url: "tunnel.company.com:7000"
  token: "team-token-abc123"

tunnels:
  # Frontend
  - name: web
    description: "React frontend"
    type: http
    local_port: 3000
    subdomain: web

  # API Gateway
  - name: gateway
    description: "API Gateway"
    type: http
    local_port: 8000
    subdomain: api

  # User Service
  - name: users
    description: "User microservice"
    type: http
    local_port: 8001
    subdomain: users

  # Order Service
  - name: orders
    description: "Order microservice"
    type: http
    local_port: 8002
    subdomain: orders

  # PostgreSQL
  - name: postgres
    description: "PostgreSQL"
    type: tcp
    local_port: 5432
    remote_port: 15432

  # Redis
  - name: redis
    description: "Redis cache"
    type: tcp
    local_port: 6379
    remote_port: 16379

  # RabbitMQ
  - name: rabbitmq
    description: "RabbitMQ"
    type: tcp
    local_port: 5672
    remote_port: 15672
```

**Access**:
- Frontend: `http://web.tunnel.company.com`
- API: `http://api.tunnel.company.com`
- Database: `tunnel.company.com:15432`
- Redis: `tunnel.company.com:16379`

---

### Development Environment

Solo developer setup with common tools.

```yaml
server:
  url: "my-vps.com:7000"
  token: "my-personal-token"

tunnels:
  # Main project
  - name: dev
    description: "Current project"
    type: http
    local_port: 8080
    subdomain: dev

  # Storybook
  - name: storybook
    description: "Component library"
    type: http
    local_port: 6006
    subdomain: storybook

  # API docs
  - name: docs
    description: "Swagger UI"
    type: http
    local_port: 8000
    subdomain: docs

  # Database
  - name: db
    description: "PostgreSQL"
    type: tcp
    local_port: 5432
    remote_port: 5432

  # SSH
  - name: ssh
    description: "SSH access"
    type: tcp
    local_port: 22
    remote_port: 2222
```

---

## Tips & Best Practices

### Naming Conventions

| Good | Avoid |
|------|-------|
| `api`, `web`, `db` | `my-project-api-v2-new` |
| `frontend`, `backend` | `test123` |
| `staging`, `demo` | Names with spaces |

### Port Selection

| Service | Suggested Remote Port |
|---------|----------------------|
| PostgreSQL (5432) | 15432 |
| MySQL (3306) | 13306 |
| MongoDB (27017) | 27017 |
| Redis (6379) | 16379 |
| SSH (22) | 2222 |

### Security Tips

1. Never expose production databases
2. Use strong tokens
3. Keep `tunnels.yaml` out of version control
4. Use HTTPS for sensitive APIs

---

## Navigation

| Previous | Up | Next |
|----------|-----|------|
| [API Reference](../api/) | [Documentation Index](../) | [Troubleshooting](../troubleshooting/) |

---

[Back to Index](../) | [API Reference](../api/) | [Troubleshooting](../troubleshooting/) | [Architecture](../architecture/)

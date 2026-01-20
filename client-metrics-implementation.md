# Client-Side Metrics Implementation Guide

## Overview

Implement request-level metrics collection in the tunnel client to report timing data to the tunnel server. This enables diagnosing slow requests and monitoring per-tunnel activity.

## Server API Endpoint

The tunnel server now has an endpoint to receive metrics from clients:

```
POST /api/metrics/report
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "metrics": [
    {
      "tunnel_name": "notes",
      "request_path": "/api/users",
      "request_method": "GET",
      "status_code": 200,
      "response_time_ms": 145,
      "bytes_sent": 256,
      "bytes_received": 1024,
      "client_ip": "192.168.1.100",
      "timestamp": "2025-12-30T23:45:00.000Z"
    }
  ]
}
```

### Authentication

The client must authenticate using a JWT token obtained from the login endpoint:

```
POST /api/auth/login
Content-Type: application/json

{"email": "user@example.com", "password": "password"}
```

Response:
```json
{"access_token": "eyJ...", "token_type": "bearer", "user": {...}}
```

Use the `access_token` as a Bearer token for the metrics report endpoint.

## Implementation Requirements

### 1. Metrics Middleware

Create middleware that wraps HTTP request handling to capture:

- **tunnel_name**: Name of the tunnel handling the request
- **request_path**: URL path (e.g., `/api/users`)
- **request_method**: HTTP method (GET, POST, PUT, DELETE, etc.)
- **status_code**: HTTP response status code
- **response_time_ms**: Time from request received to response sent (integer milliseconds)
- **bytes_sent**: Request body size in bytes
- **bytes_received**: Response body size in bytes
- **client_ip**: IP address of the client making the request (optional)
- **timestamp**: ISO 8601 timestamp when request was processed

### 2. Metrics Buffer

Buffer metrics locally before sending to reduce network overhead:

```python
class MetricsBuffer:
    def __init__(self, max_size=100, flush_interval_seconds=30):
        self.buffer = []
        self.max_size = max_size
        self.flush_interval = flush_interval_seconds

    def add(self, metric: dict):
        self.buffer.append(metric)
        if len(self.buffer) >= self.max_size:
            self.flush()

    def flush(self):
        if not self.buffer:
            return
        # Send to server
        metrics_to_send = self.buffer.copy()
        self.buffer.clear()
        self._send_to_server(metrics_to_send)
```

### 3. Metrics Reporter

Periodically send buffered metrics to the server:

```python
import requests
import threading
import time

class MetricsReporter:
    def __init__(self, server_url: str, auth_token: str):
        self.server_url = server_url
        self.auth_token = auth_token
        self.buffer = MetricsBuffer()
        self._start_periodic_flush()

    def record(self, tunnel_name: str, request, response, elapsed_ms: int):
        self.buffer.add({
            "tunnel_name": tunnel_name,
            "request_path": request.path,
            "request_method": request.method,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "bytes_sent": len(request.body or b''),
            "bytes_received": response.content_length or 0,
            "client_ip": request.remote_addr,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

    def _send_metrics(self, metrics: list):
        try:
            requests.post(
                f"{self.server_url}/api/metrics/report",
                json={"metrics": metrics},
                headers={"Authorization": f"Bearer {self.auth_token}"},
                timeout=5
            )
        except Exception as e:
            # Log error but don't crash - metrics are non-critical
            print(f"Failed to send metrics: {e}")

    def _start_periodic_flush(self):
        def flush_loop():
            while True:
                time.sleep(30)
                self.buffer.flush()

        thread = threading.Thread(target=flush_loop, daemon=True)
        thread.start()
```

### 4. Integration with Tunnel Proxy

Wrap the HTTP proxy handler to capture timing:

```python
import time

class MetricsMiddleware:
    def __init__(self, reporter: MetricsReporter, tunnel_name: str):
        self.reporter = reporter
        self.tunnel_name = tunnel_name

    async def handle_request(self, request, next_handler):
        start_time = time.perf_counter()

        # Forward request to local service
        response = await next_handler(request)

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Record metric
        self.reporter.record(
            tunnel_name=self.tunnel_name,
            request=request,
            response=response,
            elapsed_ms=elapsed_ms
        )

        return response
```

## Configuration

Add these configuration options to the client:

```ini
# Enable/disable metrics reporting
metrics_enabled = true

# Server URL for metrics reporting
metrics_server_url = https://tunnel.ersantana.com:8000

# How often to flush metrics (seconds)
metrics_flush_interval = 30

# Maximum metrics to buffer before forcing flush
metrics_buffer_size = 100

# Credentials for authentication
metrics_email = user@example.com
metrics_password = password
```

Or via environment variables:
```bash
TUNNEL_METRICS_ENABLED=true
TUNNEL_METRICS_SERVER_URL=https://tunnel.ersantana.com:8000
TUNNEL_METRICS_FLUSH_INTERVAL=30
TUNNEL_METRICS_BUFFER_SIZE=100
```

## Data Flow

```
Client Request
     │
     ▼
┌─────────────────┐
│ Metrics         │ ◄── Start timer
│ Middleware      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Local Service   │ ◄── Your app (e.g., localhost:5000)
│ (via frp)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Metrics         │ ◄── Stop timer, record metric
│ Middleware      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Metrics Buffer  │ ◄── Buffer locally
└────────┬────────┘
         │ (every 30s or when buffer full)
         ▼
┌─────────────────┐
│ Tunnel Server   │ ◄── POST /api/metrics/report
│ (port 8000)     │
└─────────────────┘
```

## Error Handling

- **Network failures**: Log and discard metrics (non-critical data)
- **Auth failures**: Re-authenticate and retry once
- **Server unavailable**: Buffer locally, retry on next flush
- **Buffer overflow**: Drop oldest metrics if buffer exceeds limit

## Testing

Test the metrics endpoint manually:

```bash
# Get auth token
TOKEN=$(curl -s -X POST https://tunnel.ersantana.com:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@localhost","password":"your-password"}' \
  | jq -r '.access_token')

# Send test metrics
curl -X POST https://tunnel.ersantana.com:8000/api/metrics/report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "metrics": [
      {
        "tunnel_name": "notes",
        "request_path": "/test",
        "request_method": "GET",
        "status_code": 200,
        "response_time_ms": 150,
        "bytes_sent": 0,
        "bytes_received": 1024,
        "timestamp": "2025-12-30T23:45:00.000Z"
      }
    ]
  }'
```

Expected response:
```json
{"stored": 1}
```

## Dashboard View

Once metrics are reported, they appear in the tunnel server admin dashboard under the **Metrics** tab:

- Filter by tunnel name
- Filter by minimum response time (to find slow requests)
- Color-coded response times:
  - Green: < 500ms
  - Yellow: 500-1000ms
  - Red: > 1000ms

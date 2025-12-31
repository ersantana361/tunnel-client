# Server Metrics Query Endpoints

This document specifies the endpoints the tunnel-server needs to implement for the tunnel-client metrics dashboard.

## Prerequisites

The server already has `POST /api/metrics/report` to receive metrics from the metrics-proxy. The endpoints below expose stored metrics for querying and visualization.

## Endpoints

### `GET /api/metrics`

Query stored request metrics with filtering and pagination.

**Authentication**: Bearer token (JWT)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tunnel_name` | string | No | - | Filter by tunnel name |
| `min_response_time` | int | No | - | Only requests slower than N ms |
| `max_response_time` | int | No | - | Only requests faster than N ms |
| `status_code` | int | No | - | Filter by HTTP status code |
| `method` | string | No | - | Filter by HTTP method (GET, POST, etc.) |
| `limit` | int | No | 100 | Max results (1-1000) |
| `offset` | int | No | 0 | Pagination offset |

**Request:**
```http
GET /api/metrics?tunnel_name=myapp&min_response_time=500&limit=50
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "metrics": [
    {
      "id": 1234,
      "tunnel_name": "myapp",
      "request_path": "/api/users",
      "request_method": "GET",
      "status_code": 200,
      "response_time_ms": 750,
      "bytes_sent": 256,
      "bytes_received": 1024,
      "client_ip": "192.168.1.100",
      "timestamp": "2025-12-30T23:45:00.000Z"
    }
  ],
  "total": 1500,
  "limit": 50,
  "offset": 0
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `400 Bad Request`: Invalid query parameters

---

### `GET /api/metrics/summary`

Get aggregated statistics for a time period.

**Authentication**: Bearer token (JWT)

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tunnel_name` | string | No | - | Filter by tunnel (all if omitted) |
| `period` | string | No | `1h` | Time window: `1h`, `24h`, `7d` |

**Request:**
```http
GET /api/metrics/summary?tunnel_name=myapp&period=24h
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "tunnel_name": "myapp",
  "period": "24h",
  "total_requests": 5000,
  "avg_response_time_ms": 145,
  "p50_response_time_ms": 120,
  "p95_response_time_ms": 450,
  "p99_response_time_ms": 890,
  "min_response_time_ms": 12,
  "max_response_time_ms": 2500,
  "total_bytes_in": 5120000,
  "total_bytes_out": 20480000,
  "status_codes": {
    "2xx": 4800,
    "3xx": 50,
    "4xx": 100,
    "5xx": 50
  },
  "requests_per_minute": 3.47,
  "error_rate": 0.03
}
```

**Notes:**
- `tunnel_name` in response is `null` if querying all tunnels
- Percentiles (p50, p95, p99) should be calculated from response time distribution
- `error_rate` = (4xx + 5xx) / total_requests

---

### `GET /api/metrics/tunnels`

List all tunnels with their latest metrics summary.

**Authentication**: Bearer token (JWT)

**Request:**
```http
GET /api/metrics/tunnels
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
{
  "tunnels": [
    {
      "tunnel_name": "myapp",
      "total_requests_1h": 500,
      "avg_response_time_1h": 145,
      "p95_response_time_1h": 450,
      "total_bytes_in_1h": 512000,
      "total_bytes_out_1h": 2048000,
      "error_rate_1h": 0.02,
      "last_request": "2025-12-30T23:45:00.000Z",
      "status": "active"
    },
    {
      "tunnel_name": "notes",
      "total_requests_1h": 50,
      "avg_response_time_1h": 89,
      "p95_response_time_1h": 200,
      "total_bytes_in_1h": 25000,
      "total_bytes_out_1h": 100000,
      "error_rate_1h": 0.0,
      "last_request": "2025-12-30T22:30:00.000Z",
      "status": "active"
    }
  ]
}
```

**Notes:**
- `status` can be: `active` (request in last 5 min), `idle` (no recent requests), `unknown`
- All `_1h` suffix metrics are for the last hour

---

## Database Schema (Suggested)

```sql
CREATE TABLE request_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tunnel_name VARCHAR(255) NOT NULL,
    request_path VARCHAR(2048) NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    bytes_sent INTEGER NOT NULL DEFAULT 0,
    bytes_received INTEGER NOT NULL DEFAULT 0,
    client_ip VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    INDEX idx_metrics_user_tunnel (user_id, tunnel_name),
    INDEX idx_metrics_timestamp (timestamp),
    INDEX idx_metrics_response_time (response_time_ms)
);
```

---

## Data Retention

Suggested retention policy:
- Keep detailed metrics for 7 days
- Aggregate hourly data for 30 days
- Aggregate daily data for 1 year

Example cleanup query:
```sql
DELETE FROM request_metrics
WHERE timestamp < NOW() - INTERVAL '7 days';
```

---

## Implementation Notes

1. **Pagination**: Always include `total` count for UI pagination
2. **Performance**: Use appropriate indexes and consider query limits
3. **Percentiles**: Calculate using approximate algorithms for large datasets (e.g., t-digest)
4. **Timezones**: Store and return all timestamps in UTC (ISO 8601 format)
5. **User Isolation**: Always filter by authenticated user's tunnels

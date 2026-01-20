#!/usr/bin/env python3
"""
Metrics Proxy - HTTP reverse proxy that captures request timing metrics
and reports them to the tunnel server.
"""

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Optional

import aiohttp
from aiohttp import web

# Configuration
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8080"))
SERVER_URL = os.environ.get("SERVER_URL", "")
TARGETS_FILE = os.environ.get("TARGETS_FILE", "/etc/frp/tunnel_targets.json")
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "/etc/frp/credentials.json")
BUFFER_SIZE = int(os.environ.get("METRICS_BUFFER_SIZE", "100"))
FLUSH_INTERVAL = int(os.environ.get("METRICS_FLUSH_INTERVAL", "30"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics-proxy")


class MetricsBuffer:
    """Buffer metrics before sending to server"""

    def __init__(self, max_size: int = 100):
        self.buffer: deque = deque(maxlen=max_size * 2)  # Allow some overflow
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def add(self, metric: dict):
        async with self._lock:
            self.buffer.append(metric)

    async def flush(self) -> list:
        async with self._lock:
            metrics = list(self.buffer)
            self.buffer.clear()
            return metrics

    def __len__(self):
        return len(self.buffer)


class MetricsReporter:
    """Reports metrics to tunnel server"""

    def __init__(self, server_url: str, credentials_file: str):
        self.server_url = server_url
        self.credentials_file = credentials_file
        self._access_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _load_credentials(self) -> Optional[dict]:
        """Load credentials from file"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
        return None

    async def get_token(self) -> Optional[str]:
        """Get access token from credentials"""
        if self._access_token:
            return self._access_token

        creds = self._load_credentials()
        if creds and 'access_token' in creds:
            self._access_token = creds['access_token']
            return self._access_token

        return None

    async def report(self, metrics: list) -> bool:
        """Send metrics to server"""
        if not metrics:
            return True

        if not self.server_url:
            logger.debug("No server URL configured, discarding metrics")
            return False

        token = await self.get_token()
        if not token:
            logger.warning("No access token available, discarding metrics")
            return False

        try:
            session = await self.get_session()
            async with session.post(
                f"{self.server_url}/api/metrics/report",
                json={"metrics": metrics},
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Reported {data.get('stored', len(metrics))} metrics to server")
                    return True
                elif resp.status == 401:
                    # Token expired, clear it
                    self._access_token = None
                    logger.warning("Access token expired, will retry with fresh token")
                    return False
                else:
                    logger.warning(f"Failed to report metrics: HTTP {resp.status}")
                    return False
        except asyncio.TimeoutError:
            logger.warning("Timeout reporting metrics to server")
            return False
        except Exception as e:
            logger.warning(f"Error reporting metrics: {e}")
            return False


class TargetsManager:
    """Manages tunnel target mappings"""

    def __init__(self, targets_file: str):
        self.targets_file = targets_file
        self._targets: dict = {}
        self._last_modified: float = 0

    def _reload_if_changed(self):
        """Reload targets file if it has changed"""
        try:
            if not os.path.exists(self.targets_file):
                return

            mtime = os.path.getmtime(self.targets_file)
            if mtime > self._last_modified:
                with open(self.targets_file, 'r') as f:
                    self._targets = json.load(f)
                self._last_modified = mtime
                logger.info(f"Loaded {len(self._targets)} tunnel targets")
        except Exception as e:
            logger.warning(f"Failed to reload targets: {e}")

    def get_target(self, tunnel_name: str) -> Optional[dict]:
        """Get target for a tunnel"""
        self._reload_if_changed()
        return self._targets.get(tunnel_name)


class MetricsProxy:
    """HTTP reverse proxy with metrics collection and WebSocket support"""

    def __init__(self):
        self.buffer = MetricsBuffer(max_size=BUFFER_SIZE)
        self.reporter = MetricsReporter(SERVER_URL, CREDENTIALS_FILE)
        self.targets = TargetsManager(TARGETS_FILE)
        self._flush_task: Optional[asyncio.Task] = None
        self._proxy_session: Optional[aiohttp.ClientSession] = None

    def _is_websocket_request(self, request: web.Request) -> bool:
        """Check if request is a WebSocket upgrade request"""
        upgrade = request.headers.get("Upgrade", "").lower()
        connection = request.headers.get("Connection", "").lower()
        return upgrade == "websocket" and "upgrade" in connection

    async def get_proxy_session(self) -> aiohttp.ClientSession:
        if self._proxy_session is None or self._proxy_session.closed:
            # Connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                keepalive_timeout=30
            )
            # Disable auto_decompress to pass through compressed content as-is
            self._proxy_session = aiohttp.ClientSession(
                connector=connector,
                auto_decompress=False
            )
        return self._proxy_session

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket proxy connection"""
        start_time = time.perf_counter()

        # Get tunnel name from header
        tunnel_name = request.headers.get("X-Tunnel-Name", "unknown")

        # Get target for this tunnel
        target = self.targets.get_target(tunnel_name)
        if not target:
            logger.warning(f"No target found for WebSocket tunnel: {tunnel_name}")
            raise web.HTTPBadGateway(text=f"No target configured for tunnel: {tunnel_name}")

        target_host = target.get("host", "127.0.0.1")
        target_port = target.get("port", 8080)

        # Build WebSocket target URL
        target_url = f"ws://{target_host}:{target_port}{request.path_qs}"

        logger.info(f"WebSocket connection: {tunnel_name} -> {target_url}")

        # Prepare headers for upstream connection
        headers = {}
        skip_headers = {'host', 'x-tunnel-name', 'sec-websocket-key',
                        'sec-websocket-version', 'sec-websocket-extensions',
                        'sec-websocket-protocol', 'upgrade', 'connection'}
        for key, value in request.headers.items():
            if key.lower() not in skip_headers:
                headers[key] = value

        # Add forwarding headers
        client_ip = request.remote or "unknown"
        headers['X-Forwarded-For'] = client_ip
        headers['X-Forwarded-Proto'] = request.scheme
        headers['X-Forwarded-Host'] = request.host

        # Accept the client WebSocket connection
        ws_client = web.WebSocketResponse()
        await ws_client.prepare(request)

        bytes_sent = 0
        bytes_received = 0

        try:
            # Connect to target WebSocket
            session = await self.get_proxy_session()
            async with session.ws_connect(
                target_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=None)  # No timeout for WebSocket
            ) as ws_server:

                async def forward_client_to_server():
                    """Forward messages from client to server"""
                    nonlocal bytes_sent
                    try:
                        async for msg in ws_client:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await ws_server.send_str(msg.data)
                                bytes_sent += len(msg.data.encode())
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await ws_server.send_bytes(msg.data)
                                bytes_sent += len(msg.data)
                            elif msg.type == aiohttp.WSMsgType.PING:
                                await ws_server.ping(msg.data)
                            elif msg.type == aiohttp.WSMsgType.PONG:
                                await ws_server.pong(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception as e:
                        logger.debug(f"Client->Server forward ended: {e}")
                    finally:
                        if not ws_server.closed:
                            await ws_server.close()

                async def forward_server_to_client():
                    """Forward messages from server to client"""
                    nonlocal bytes_received
                    try:
                        async for msg in ws_server:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await ws_client.send_str(msg.data)
                                bytes_received += len(msg.data.encode())
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await ws_client.send_bytes(msg.data)
                                bytes_received += len(msg.data)
                            elif msg.type == aiohttp.WSMsgType.PING:
                                await ws_client.ping(msg.data)
                            elif msg.type == aiohttp.WSMsgType.PONG:
                                await ws_client.pong(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception as e:
                        logger.debug(f"Server->Client forward ended: {e}")
                    finally:
                        if not ws_client.closed:
                            await ws_client.close()

                # Run both forwarding tasks concurrently
                await asyncio.gather(
                    forward_client_to_server(),
                    forward_server_to_client(),
                    return_exceptions=True
                )

        except aiohttp.ClientConnectorError as e:
            logger.error(f"WebSocket connection failed for {tunnel_name}: {e}")
            if not ws_client.closed:
                await ws_client.close(code=1011, message=b"Backend unavailable")
        except Exception as e:
            logger.error(f"WebSocket error for {tunnel_name}: {e}")
            if not ws_client.closed:
                await ws_client.close(code=1011, message=b"Internal error")

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Record metric for WebSocket connection
        metric = {
            "tunnel_name": tunnel_name,
            "request_path": request.path,
            "request_method": "WEBSOCKET",
            "status_code": 101,  # WebSocket upgrade status
            "response_time_ms": elapsed_ms,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.buffer.add(metric)

        logger.info(
            f"WebSocket closed: {tunnel_name} "
            f"(duration={elapsed_ms}ms, sent={bytes_sent}b, recv={bytes_received}b)"
        )

        return ws_client

    async def start_flush_loop(self):
        """Periodically flush metrics to server"""
        while True:
            try:
                await asyncio.sleep(FLUSH_INTERVAL)
                metrics = await self.buffer.flush()
                if metrics:
                    await self.reporter.report(metrics)
            except asyncio.CancelledError:
                # Final flush on shutdown
                metrics = await self.buffer.flush()
                if metrics:
                    await self.reporter.report(metrics)
                raise
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming request, proxy it, and record metrics"""
        # Check for WebSocket upgrade request
        if self._is_websocket_request(request):
            return await self.handle_websocket(request)

        start_time = time.perf_counter()

        # Get tunnel name from header
        tunnel_name = request.headers.get("X-Tunnel-Name", "unknown")

        # Get target for this tunnel
        target = self.targets.get_target(tunnel_name)
        if not target:
            logger.warning(f"No target found for tunnel: {tunnel_name}")
            return web.Response(
                status=502,
                text=f"No target configured for tunnel: {tunnel_name}"
            )

        target_host = target.get("host", "127.0.0.1")
        target_port = target.get("port", 8080)

        # Build target URL
        target_url = f"http://{target_host}:{target_port}{request.path_qs}"

        # Read request body
        try:
            request_body = await request.read()
        except Exception:
            request_body = b""

        bytes_sent = len(request_body)

        # Prepare headers (remove hop-by-hop headers and our custom header)
        headers = {}
        hop_by_hop = {'connection', 'keep-alive', 'transfer-encoding',
                      'te', 'trailer', 'upgrade', 'x-tunnel-name'}
        for key, value in request.headers.items():
            if key.lower() not in hop_by_hop:
                headers[key] = value

        # Add/update forwarding headers
        client_ip = request.remote or "unknown"
        if 'X-Forwarded-For' in headers:
            headers['X-Forwarded-For'] = f"{headers['X-Forwarded-For']}, {client_ip}"
        else:
            headers['X-Forwarded-For'] = client_ip

        headers['X-Forwarded-Proto'] = request.scheme
        headers['X-Forwarded-Host'] = request.host

        # Proxy the request
        status_code = 502
        bytes_received = 0
        response_headers = {}
        response_body = b""

        try:
            session = await self.get_proxy_session()
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request_body,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                status_code = resp.status
                response_body = await resp.read()
                bytes_received = len(response_body)

                # Copy response headers (excluding hop-by-hop)
                for key, value in resp.headers.items():
                    if key.lower() not in hop_by_hop:
                        response_headers[key] = value

        except asyncio.TimeoutError:
            status_code = 504
            response_body = b"Gateway Timeout"
        except aiohttp.ClientConnectorError as e:
            status_code = 502
            response_body = f"Bad Gateway: {e}".encode()
        except Exception as e:
            status_code = 502
            response_body = f"Proxy Error: {e}".encode()
            logger.error(f"Proxy error for {tunnel_name}: {e}")

        # Calculate elapsed time
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Record metric
        metric = {
            "tunnel_name": tunnel_name,
            "request_path": request.path,
            "request_method": request.method,
            "status_code": status_code,
            "response_time_ms": elapsed_ms,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.buffer.add(metric)

        # Log request
        logger.debug(
            f"{request.method} {request.path} -> {tunnel_name} "
            f"({status_code}, {elapsed_ms}ms, {bytes_sent}/{bytes_received}b)"
        )

        # Force flush if buffer is full
        if len(self.buffer) >= BUFFER_SIZE:
            metrics = await self.buffer.flush()
            if metrics:
                asyncio.create_task(self.reporter.report(metrics))

        # Return response
        return web.Response(
            status=status_code,
            body=response_body,
            headers=response_headers
        )

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "buffer_size": len(self.buffer),
            "targets_loaded": len(self.targets._targets)
        })

    async def on_startup(self, app: web.Application):
        """Start background tasks"""
        self._flush_task = asyncio.create_task(self.start_flush_loop())
        logger.info(f"Metrics proxy started on port {PROXY_PORT}")
        logger.info(f"Server URL: {SERVER_URL or 'not configured'}")
        logger.info(f"Targets file: {TARGETS_FILE}")

    async def on_cleanup(self, app: web.Application):
        """Cleanup on shutdown"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        if self._proxy_session and not self._proxy_session.closed:
            await self._proxy_session.close()

        await self.reporter.close()
        logger.info("Metrics proxy stopped")


def create_app() -> web.Application:
    """Create the aiohttp application"""
    proxy = MetricsProxy()

    app = web.Application()
    app.router.add_get("/health", proxy.health_check)
    app.router.add_route("*", "/{path:.*}", proxy.handle_request)

    app.on_startup.append(proxy.on_startup)
    app.on_cleanup.append(proxy.on_cleanup)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=PROXY_PORT, print=None)

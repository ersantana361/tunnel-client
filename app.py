#!/usr/bin/env python3
"""
Tunnel Client - User Interface
Connects to tunnel server with user credentials
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import subprocess
import os
import signal
import stat
import time
import logging
import argparse
import json
import requests
from typing import Optional, Literal, Dict, Any
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CREDENTIALS_FILE = "credentials.json"
FRPC_CONFIG = "/etc/frp/frpc.ini"
FRPC_PID_FILE = "/tmp/frpc.pid"
FRPC_LOG_FILE = "/tmp/frpc.log"

# Global credentials cache
_credentials_cache: Optional[Dict[str, Any]] = None


# =============================================================================
# Credentials Management
# =============================================================================

def load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from file"""
    global _credentials_cache

    if not os.path.exists(CREDENTIALS_FILE):
        return None

    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
        _credentials_cache = creds
        return creds
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load credentials: {e}")
        return None


def save_credentials(server_url: str, access_token: str, tunnel_token: str, user_email: str) -> bool:
    """Save credentials to file"""
    global _credentials_cache

    creds = {
        "server_url": server_url,
        "access_token": access_token,
        "tunnel_token": tunnel_token,
        "user_email": user_email
    }

    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        os.chmod(CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        _credentials_cache = creds
        logger.info(f"Credentials saved for {user_email}")
        return True
    except IOError as e:
        logger.error(f"Failed to save credentials: {e}")
        return False


def clear_credentials() -> bool:
    """Clear credentials file"""
    global _credentials_cache

    _credentials_cache = None
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
        logger.info("Credentials cleared")
        return True
    except IOError as e:
        logger.error(f"Failed to clear credentials: {e}")
        return False


def get_credentials() -> Optional[Dict[str, Any]]:
    """Get cached credentials or load from file"""
    global _credentials_cache
    if _credentials_cache is None:
        load_credentials()
    return _credentials_cache


def get_api_headers() -> Dict[str, str]:
    """Get headers for API requests"""
    creds = get_credentials()
    if not creds:
        return {}
    return {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json"
    }


# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    creds = load_credentials()
    if creds:
        logger.info(f"Loaded credentials for {creds.get('user_email', 'unknown')}")
    else:
        logger.info("No credentials found - login required")

    # Check if frpc is installed
    if not os.path.exists("/usr/local/bin/frpc"):
        logger.warning("frpc not found at /usr/local/bin/frpc - service start will fail")
    else:
        logger.info("frpc found at /usr/local/bin/frpc")

    # Clean up stale PID file on startup
    frpc_running = False
    if os.path.exists(FRPC_PID_FILE):
        try:
            with open(FRPC_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            logger.info(f"frpc already running with PID {pid}")
            frpc_running = True
        except (ValueError, OSError, FileNotFoundError):
            logger.info("Cleaning up stale PID file")
            try:
                os.remove(FRPC_PID_FILE)
            except FileNotFoundError:
                pass

    # Auto-start frpc if we have credentials and tunnels
    if creds and not frpc_running:
        try:
            response = requests.get(
                f"{creds['server_url']}/api/tunnels",
                headers={"Authorization": f"Bearer {creds['access_token']}"},
                timeout=10
            )
            if response.status_code == 200:
                tunnels = response.json().get("tunnels", [])
                if tunnels:
                    logger.info(f"Auto-starting frpc with {len(tunnels)} tunnel(s)...")
                    # Start frpc directly here (sync)
                    try:
                        # Generate config first
                        server_url = creds["server_url"].replace("http://", "").replace("https://", "")
                        if ":" in server_url:
                            server_addr = server_url.split(":")[0]
                        else:
                            server_addr = server_url

                        config_content = f"""[common]
server_addr = {server_addr}
server_port = 7000
token = {creds['tunnel_token']}

"""
                        for tunnel in tunnels:
                            config_content += f"[{tunnel.get('name', 'unnamed')}]\n"
                            config_content += f"type = {tunnel.get('type', 'http')}\n"
                            config_content += f"local_ip = {tunnel.get('local_host', '127.0.0.1')}\n"
                            config_content += f"local_port = {tunnel.get('local_port', 8080)}\n"
                            if tunnel.get('subdomain'):
                                config_content += f"subdomain = {tunnel.get('subdomain')}\n"
                            if tunnel.get('remote_port'):
                                config_content += f"remote_port = {tunnel.get('remote_port')}\n"
                            config_content += "\n"

                        os.makedirs(os.path.dirname(FRPC_CONFIG), exist_ok=True)
                        with open(FRPC_CONFIG, 'w') as f:
                            f.write(config_content)

                        # Start frpc
                        log_file = open(FRPC_LOG_FILE, 'a')
                        process = subprocess.Popen(
                            ["/usr/local/bin/frpc", "-c", FRPC_CONFIG],
                            stdout=log_file,
                            stderr=log_file,
                            start_new_session=True
                        )
                        with open(FRPC_PID_FILE, 'w') as f:
                            f.write(str(process.pid))
                        os.chmod(FRPC_PID_FILE, stat.S_IRUSR | stat.S_IWUSR)
                        logger.info(f"Auto-started frpc with PID {process.pid}")
                    except Exception as e:
                        logger.warning(f"Auto-start frpc failed: {e}")
        except Exception as e:
            logger.warning(f"Auto-start check failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down tunnel client")


app = FastAPI(title="Tunnel Client", lifespan=lifespan)


# =============================================================================
# Request/Response Models
# =============================================================================

class LoginRequest(BaseModel):
    server_url: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TunnelCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    type: Literal["http", "https", "tcp"]
    local_port: int = Field(..., ge=1, le=65535)
    local_host: str = "127.0.0.1"
    subdomain: Optional[str] = None
    remote_port: Optional[int] = Field(None, ge=1, le=65535)


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/api/login")
async def login(request: LoginRequest):
    """Login to tunnel server"""
    server_url = request.server_url.rstrip('/')

    # Ensure server_url has protocol
    if not server_url.startswith(('http://', 'https://')):
        server_url = f"http://{server_url}"

    try:
        response = requests.post(
            f"{server_url}/api/auth/login",
            json={"email": request.email, "password": request.password},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            user = data.get("user", {})
            tunnel_token = user.get("token") or user.get("tunnel_token", "")

            save_credentials(
                server_url=server_url,
                access_token=access_token,
                tunnel_token=tunnel_token,
                user_email=request.email
            )

            # Auto-start frpc if there are tunnels
            try:
                tunnels_response = requests.get(
                    f"{server_url}/api/tunnels",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10
                )
                if tunnels_response.status_code == 200:
                    tunnels = tunnels_response.json().get("tunnels", [])
                    if tunnels:
                        # Start frpc in background
                        import asyncio
                        asyncio.create_task(auto_start_service())
            except Exception as e:
                logger.warning(f"Auto-start check failed: {e}")

            return {
                "message": "Login successful",
                "email": request.email,
                "server_url": server_url
            }
        elif response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        else:
            error_detail = response.json().get("detail", "Login failed")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to server: {server_url}")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Server connection timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logout")
async def logout():
    """Logout and clear credentials"""
    # Stop frpc if running
    status = await get_status()
    if status["running"]:
        await stop_service()

    clear_credentials()
    return {"message": "Logged out successfully"}


@app.get("/api/auth/status")
async def auth_status():
    """Get authentication status"""
    creds = get_credentials()
    if not creds:
        return {
            "authenticated": False,
            "email": None,
            "server_url": None
        }

    return {
        "authenticated": True,
        "email": creds.get("user_email"),
        "server_url": creds.get("server_url")
    }


# =============================================================================
# Tunnel Endpoints (Server API)
# =============================================================================

@app.get("/api/tunnels")
async def list_tunnels():
    """Get all tunnels from server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        response = requests.get(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            raise HTTPException(status_code=401, detail="Session expired - please login again")

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch tunnels")

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


@app.post("/api/tunnels")
async def create_tunnel(request: TunnelCreateRequest):
    """Create a new tunnel on server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate type requirements
    if request.type in ("http", "https") and not request.subdomain:
        raise HTTPException(status_code=400, detail="Subdomain is required for HTTP/HTTPS tunnels")
    if request.type == "tcp" and not request.remote_port:
        raise HTTPException(status_code=400, detail="Remote port is required for TCP tunnels")

    try:
        payload = {
            "name": request.name,
            "type": request.type,
            "local_port": request.local_port,
            "local_host": request.local_host
        }
        if request.subdomain:
            payload["subdomain"] = request.subdomain
        if request.remote_port:
            payload["remote_port"] = request.remote_port

        response = requests.post(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            json=payload,
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            raise HTTPException(status_code=401, detail="Session expired - please login again")

        if response.status_code == 400:
            error = response.json().get("detail", "Invalid tunnel configuration")
            raise HTTPException(status_code=400, detail=error)

        if response.status_code not in (200, 201):
            try:
                error_data = response.json()
                detail = error_data.get("detail", f"Server returned {response.status_code}")
            except:
                detail = f"Server returned {response.status_code}: {response.text[:200]}"
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


@app.delete("/api/tunnels/{tunnel_id}")
async def delete_tunnel(tunnel_id: int):
    """Delete a tunnel from server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        response = requests.delete(
            f"{creds['server_url']}/api/tunnels/{tunnel_id}",
            headers=get_api_headers(),
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            raise HTTPException(status_code=401, detail="Session expired - please login again")

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Tunnel not found")

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to delete tunnel")

        return {"message": "Tunnel deleted successfully"}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


async def update_tunnel_status(tunnel_id: int, is_active: bool):
    """Update tunnel status on server"""
    creds = get_credentials()
    if not creds:
        return

    try:
        requests.put(
            f"{creds['server_url']}/api/tunnels/{tunnel_id}/status",
            headers=get_api_headers(),
            json={"is_active": is_active},
            timeout=5
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to update tunnel {tunnel_id} status: {e}")


async def update_all_tunnels_status(is_active: bool):
    """Update all tunnels status on server"""
    creds = get_credentials()
    if not creds:
        return

    try:
        response = requests.get(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code == 200:
            tunnels = response.json().get("tunnels", [])
            for tunnel in tunnels:
                await update_tunnel_status(tunnel["id"], is_active)
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to update tunnels status: {e}")


# =============================================================================
# Service Control Endpoints
# =============================================================================

@app.get("/api/status")
async def get_status():
    """Check service status"""
    is_running = False
    pid = None

    if os.path.exists(FRPC_PID_FILE):
        try:
            with open(FRPC_PID_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    pid = int(content)
        except (ValueError, FileNotFoundError, IOError) as e:
            logger.warning(f"Invalid PID file: {e}")
            try:
                os.remove(FRPC_PID_FILE)
            except FileNotFoundError:
                pass
            return {"running": False, "pid": None}

        if pid:
            try:
                os.kill(pid, 0)
                is_running = True
            except OSError:
                is_running = False
                pid = None
                try:
                    os.remove(FRPC_PID_FILE)
                except FileNotFoundError:
                    pass

    return {"running": is_running, "pid": pid}


async def auto_start_service():
    """Auto-start frpc if not already running"""
    try:
        status = await get_status()
        if not status["running"]:
            logger.info("Auto-starting frpc service...")
            # Call the internal start logic directly, not the endpoint
            creds = get_credentials()
            if not creds:
                logger.warning("Auto-start: No credentials")
                return

            if not os.path.exists("/usr/local/bin/frpc"):
                logger.warning("Auto-start: frpc not found")
                return

            await regenerate_frpc_config()

            log_file = open(FRPC_LOG_FILE, 'a')
            process = subprocess.Popen(
                ["/usr/local/bin/frpc", "-c", FRPC_CONFIG],
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )

            with open(FRPC_PID_FILE, 'w') as f:
                f.write(str(process.pid))
            os.chmod(FRPC_PID_FILE, stat.S_IRUSR | stat.S_IWUSR)

            logger.info(f"Auto-start: frpc started with PID {process.pid}")
            await update_all_tunnels_status(True)
    except Exception as e:
        logger.warning(f"Auto-start failed: {e}")


@app.post("/api/start")
async def start_service():
    """Start frpc"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated - please login first")

    status = await get_status()
    if status["running"]:
        raise HTTPException(status_code=400, detail="Already running")

    if not os.path.exists("/usr/local/bin/frpc"):
        raise HTTPException(status_code=500, detail="frpc not found at /usr/local/bin/frpc")

    await regenerate_frpc_config()

    try:
        log_file = open(FRPC_LOG_FILE, 'a')

        process = subprocess.Popen(
            ["/usr/local/bin/frpc", "-c", FRPC_CONFIG],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )

        with open(FRPC_PID_FILE, 'w') as f:
            f.write(str(process.pid))
        os.chmod(FRPC_PID_FILE, stat.S_IRUSR | stat.S_IWUSR)

        logger.info(f"frpc started with PID {process.pid}")

        # Update tunnel status on server
        await update_all_tunnels_status(True)

        return {"message": "Service started", "pid": process.pid}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="frpc executable not found")
    except PermissionError as e:
        raise HTTPException(status_code=500, detail=f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Failed to start frpc: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_service():
    """Stop frpc"""
    status = await get_status()
    if not status["running"]:
        raise HTTPException(status_code=400, detail="Not running")

    pid = status["pid"]
    try:
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGTERM)

        for _ in range(50):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except OSError:
                break

        try:
            os.remove(FRPC_PID_FILE)
        except FileNotFoundError:
            pass

        logger.info(f"frpc stopped (was PID {pid})")

        # Update tunnel status on server
        await update_all_tunnels_status(False)

        return {"message": "Service stopped"}
    except ProcessLookupError:
        try:
            os.remove(FRPC_PID_FILE)
        except FileNotFoundError:
            pass
        await update_all_tunnels_status(False)
        return {"message": "Service stopped"}
    except Exception as e:
        logger.error(f"Failed to stop frpc: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/restart")
async def restart_service():
    """Restart frpc"""
    status = await get_status()
    if status["running"]:
        await stop_service()
    await start_service()
    return {"message": "Service restarted"}


# =============================================================================
# Config Generation
# =============================================================================

async def regenerate_frpc_config():
    """Generate frpc.ini from server tunnels"""
    creds = get_credentials()
    if not creds:
        logger.error("No credentials - cannot generate frpc config")
        return

    # Get tunnels from server
    try:
        response = requests.get(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            timeout=10
        )
        if response.status_code != 200:
            logger.error("Failed to fetch tunnels from server")
            return
        tunnels = response.json().get("tunnels", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch tunnels: {e}")
        return

    # Parse server URL for frpc config
    server_url = creds["server_url"]
    server_url = server_url.replace("http://", "").replace("https://", "")
    # Remove port 8000 (API port) and use 7000 (frp port)
    if ":" in server_url:
        server_addr = server_url.split(":")[0]
    else:
        server_addr = server_url
    server_port = "7000"

    # Generate config
    config_content = f"""[common]
server_addr = {server_addr}
server_port = {server_port}
token = {creds['tunnel_token']}

"""

    for tunnel in tunnels:
        name = tunnel.get('name', 'unnamed')
        tunnel_type = tunnel.get('type', 'http')
        local_port = tunnel.get('local_port', 8080)
        local_host = tunnel.get('local_host', '127.0.0.1')
        subdomain = tunnel.get('subdomain')
        remote_port = tunnel.get('remote_port')

        config_content += f"[{name}]\n"
        config_content += f"type = {tunnel_type}\n"
        config_content += f"local_ip = {local_host}\n"
        config_content += f"local_port = {local_port}\n"

        if subdomain:
            config_content += f"subdomain = {subdomain}\n"

        if remote_port:
            config_content += f"remote_port = {remote_port}\n"

        config_content += "\n"

    # Create directory
    config_dir = os.path.dirname(FRPC_CONFIG)
    os.makedirs(config_dir, exist_ok=True)
    try:
        os.chmod(config_dir, stat.S_IRWXU)
    except PermissionError:
        logger.warning(f"Could not set permissions on {config_dir}")

    # Write config
    with open(FRPC_CONFIG, 'w') as f:
        f.write(config_content)
    try:
        os.chmod(FRPC_CONFIG, stat.S_IRUSR | stat.S_IWUSR)
    except PermissionError:
        logger.warning(f"Could not set permissions on {FRPC_CONFIG}")

    logger.info(f"Generated frpc config with {len(tunnels)} tunnel(s)")


# =============================================================================
# UI
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    return get_client_html()


def get_client_html():
    """Return client UI"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Tunnel Client</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            min-height: 100vh;
        }

        .container { max-width: 900px; margin: 0 auto; }

        h1 {
            color: #38bdf8;
            margin-bottom: 30px;
            font-size: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .user-info {
            font-size: 14px;
            color: #94a3b8;
            font-weight: normal;
        }

        .user-info button {
            margin-left: 10px;
        }

        /* Login Form */
        .login-container {
            max-width: 400px;
            margin: 100px auto;
        }

        .login-box {
            background: #1e293b;
            padding: 30px;
            border-radius: 12px;
        }

        .login-box h2 {
            color: #38bdf8;
            margin-bottom: 20px;
            text-align: center;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #94a3b8;
            font-size: 13px;
        }

        .form-group input, .form-group select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #334155;
            border-radius: 6px;
            background: #0f172a;
            color: #e2e8f0;
            font-size: 14px;
        }

        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #38bdf8;
        }

        /* Status Bar */
        .status-bar {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ef4444;
        }

        .status-dot.running { background: #22c55e; }

        /* Buttons */
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-success { background: #22c55e; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-secondary { background: #64748b; color: white; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }

        /* Sections */
        .section {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .section h2 {
            color: #38bdf8;
            margin-bottom: 15px;
            font-size: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Tunnel List */
        .tunnel-list { display: grid; gap: 12px; }

        .tunnel-item {
            background: #0f172a;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #334155;
        }

        .tunnel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .tunnel-name-wrap {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .tunnel-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #64748b;
        }

        .tunnel-status-dot.active { background: #22c55e; }

        .tunnel-name {
            color: #38bdf8;
            font-weight: 600;
            font-size: 15px;
        }

        .tunnel-type {
            background: #334155;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            text-transform: uppercase;
        }

        .tunnel-details {
            color: #94a3b8;
            font-size: 13px;
            margin-bottom: 8px;
        }

        .tunnel-url {
            color: #22c55e;
            font-size: 12px;
            word-break: break-all;
        }

        .tunnel-url a {
            color: #22c55e;
            text-decoration: none;
        }

        .tunnel-url a:hover {
            text-decoration: underline;
        }

        .tunnel-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #334155;
        }

        .tunnel-last-connected {
            color: #64748b;
            font-size: 11px;
        }

        /* Create Tunnel Form */
        .create-form {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: #0f172a;
            border-radius: 6px;
            border: 1px solid #334155;
        }

        .create-form.show { display: block; }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .form-actions {
            margin-top: 15px;
            display: flex;
            gap: 10px;
        }

        /* Alerts */
        .alert {
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
        }

        .alert-success {
            background: #22c55e22;
            color: #22c55e;
            border: 1px solid #22c55e44;
        }

        .alert-error {
            background: #ef444422;
            color: #ef4444;
            border: 1px solid #ef444444;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Login Screen -->
        <div id="loginScreen" class="login-container" style="display:none">
            <div class="login-box">
                <h2>Tunnel Client</h2>
                <div id="loginAlert"></div>
                <form onsubmit="handleLogin(event)">
                    <div class="form-group">
                        <label>Server URL</label>
                        <input type="text" id="serverUrl" placeholder="http://your-server.com:8000" required>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" id="email" placeholder="user@example.com" required>
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="password" placeholder="Your password" required>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:100%;margin-top:10px">Login</button>
                </form>
            </div>
        </div>

        <!-- Main Dashboard -->
        <div id="dashboard" style="display:none">
            <h1>
                Tunnel Client
                <span class="user-info">
                    <span id="userEmail"></span>
                    <button class="btn btn-secondary btn-sm" onclick="handleLogout()">Logout</button>
                </span>
            </h1>

            <div id="alert"></div>

            <!-- Status Bar -->
            <div class="status-bar">
                <div class="status-indicator">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="statusText">Checking...</span>
                </div>
                <div>
                    <button class="btn btn-success" id="btnStart" onclick="startService()">Start</button>
                    <button class="btn btn-danger" id="btnStop" onclick="stopService()" style="display:none">Stop</button>
                    <button class="btn btn-secondary" id="btnRestart" onclick="restartService()" style="display:none">Restart</button>
                </div>
            </div>

            <!-- Tunnels Section -->
            <div class="section">
                <h2>
                    Tunnels <span id="tunnelCount" style="color:#64748b;font-weight:normal"></span>
                    <button class="btn btn-primary btn-sm" onclick="toggleCreateForm()">+ New Tunnel</button>
                </h2>

                <!-- Create Tunnel Form -->
                <div class="create-form" id="createForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Name</label>
                            <input type="text" id="tunnelName" placeholder="my-tunnel">
                        </div>
                        <div class="form-group">
                            <label>Type</label>
                            <select id="tunnelType" onchange="updateFormFields()">
                                <option value="http">HTTP</option>
                                <option value="https">HTTPS</option>
                                <option value="tcp">TCP</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Local Port</label>
                            <input type="number" id="tunnelLocalPort" placeholder="8080" min="1" max="65535">
                        </div>
                        <div class="form-group" id="subdomainGroup">
                            <label>Subdomain</label>
                            <input type="text" id="tunnelSubdomain" placeholder="myapp">
                        </div>
                        <div class="form-group" id="remotePortGroup" style="display:none">
                            <label>Remote Port</label>
                            <input type="number" id="tunnelRemotePort" placeholder="5432" min="1" max="65535">
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-primary" onclick="createTunnel()">Create Tunnel</button>
                        <button class="btn btn-secondary" onclick="toggleCreateForm()">Cancel</button>
                    </div>
                </div>

                <div class="tunnel-list" id="tunnelList">
                    <p style="color: #64748b">Loading...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let statusInterval = null;

        // Initialize
        checkAuth();

        async function checkAuth() {
            try {
                const res = await fetch('/api/auth/status');
                const data = await res.json();

                if (data.authenticated) {
                    showDashboard(data.email);
                } else {
                    showLogin();
                }
            } catch (e) {
                console.error('Auth check failed:', e);
                showLogin();
            }
        }

        function showLogin() {
            document.getElementById('loginScreen').style.display = 'block';
            document.getElementById('dashboard').style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }

        function showDashboard(email) {
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('dashboard').style.display = 'block';
            document.getElementById('userEmail').textContent = email;
            loadStatus();
            loadTunnels();
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(() => {
                loadStatus();
                loadTunnels();
            }, 5000);
        }

        async function handleLogin(e) {
            e.preventDefault();
            const serverUrl = document.getElementById('serverUrl').value;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({server_url: serverUrl, email, password})
                });

                if (res.ok) {
                    showDashboard(email);
                } else {
                    const error = await res.json();
                    showLoginAlert(error.detail || 'Login failed', 'error');
                }
            } catch (e) {
                showLoginAlert('Network error', 'error');
            }
        }

        async function handleLogout() {
            try {
                await fetch('/api/logout', {method: 'POST'});
            } catch (e) {}
            showLogin();
        }

        function showLoginAlert(message, type) {
            const container = document.getElementById('loginAlert');
            container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => container.innerHTML = '', 3000);
        }

        async function loadStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) return;
                const data = await res.json();

                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                const btnStart = document.getElementById('btnStart');
                const btnStop = document.getElementById('btnStop');
                const btnRestart = document.getElementById('btnRestart');

                if (data.running) {
                    dot.classList.add('running');
                    text.textContent = 'Connected (PID: ' + data.pid + ')';
                    btnStart.style.display = 'none';
                    btnStop.style.display = 'inline-block';
                    btnRestart.style.display = 'inline-block';
                } else {
                    dot.classList.remove('running');
                    text.textContent = 'Disconnected';
                    btnStart.style.display = 'inline-block';
                    btnStop.style.display = 'none';
                    btnRestart.style.display = 'none';
                }
            } catch (e) {
                console.error('Failed to load status:', e);
            }
        }

        async function loadTunnels() {
            try {
                const res = await fetch('/api/tunnels');
                if (res.status === 401) {
                    showLogin();
                    return;
                }
                if (!res.ok) {
                    showAlert('Failed to load tunnels', 'error');
                    return;
                }
                const data = await res.json();
                const list = document.getElementById('tunnelList');
                const countEl = document.getElementById('tunnelCount');

                const tunnels = data.tunnels || [];
                countEl.textContent = '(' + tunnels.length + ')';

                if (tunnels.length === 0) {
                    list.innerHTML = '<div class="empty-state">No tunnels yet. Click "+ New Tunnel" to create one.</div>';
                    return;
                }

                list.innerHTML = '';

                tunnels.forEach(t => {
                    const item = document.createElement('div');
                    item.className = 'tunnel-item';

                    const isActive = t.is_active;
                    const statusClass = isActive ? 'active' : '';

                    let detailText = t.local_host + ':' + t.local_port;
                    let urlHtml = '';

                    if (t.public_url) {
                        urlHtml = `<div class="tunnel-url"><a href="${t.public_url}" target="_blank">${t.public_url}</a></div>`;
                    } else if (t.subdomain) {
                        detailText += ' → ' + t.subdomain + '.[server]';
                    } else if (t.remote_port) {
                        detailText += ' → [server]:' + t.remote_port;
                    }

                    let lastConnected = '';
                    if (t.last_connected) {
                        lastConnected = 'Last connected: ' + new Date(t.last_connected).toLocaleString();
                    }

                    item.innerHTML = `
                        <div class="tunnel-header">
                            <div class="tunnel-name-wrap">
                                <div class="tunnel-status-dot ${statusClass}"></div>
                                <span class="tunnel-name">${t.name}</span>
                                <span class="tunnel-type">${t.type}</span>
                            </div>
                            <button class="btn btn-danger btn-sm" onclick="deleteTunnel(${t.id})">Delete</button>
                        </div>
                        <div class="tunnel-details">${detailText}</div>
                        ${urlHtml}
                        <div class="tunnel-meta">
                            <span class="tunnel-last-connected">${lastConnected}</span>
                            <span style="color: ${isActive ? '#22c55e' : '#64748b'}; font-size: 12px;">
                                ${isActive ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    `;

                    list.appendChild(item);
                });
            } catch (e) {
                console.error('Failed to load tunnels:', e);
                showAlert('Network error loading tunnels', 'error');
            }
        }

        function toggleCreateForm() {
            const form = document.getElementById('createForm');
            form.classList.toggle('show');
        }

        function updateFormFields() {
            const type = document.getElementById('tunnelType').value;
            const subdomainGroup = document.getElementById('subdomainGroup');
            const remotePortGroup = document.getElementById('remotePortGroup');

            if (type === 'tcp') {
                subdomainGroup.style.display = 'none';
                remotePortGroup.style.display = 'block';
            } else {
                subdomainGroup.style.display = 'block';
                remotePortGroup.style.display = 'none';
            }
        }

        async function createTunnel() {
            const name = document.getElementById('tunnelName').value.trim();
            const type = document.getElementById('tunnelType').value;
            const localPort = parseInt(document.getElementById('tunnelLocalPort').value);
            const subdomain = document.getElementById('tunnelSubdomain').value.trim();
            const remotePort = parseInt(document.getElementById('tunnelRemotePort').value);

            if (!name || !localPort) {
                showAlert('Name and local port are required', 'error');
                return;
            }

            const payload = {name, type, local_port: localPort};
            if (type === 'tcp') {
                if (!remotePort) {
                    showAlert('Remote port is required for TCP tunnels', 'error');
                    return;
                }
                payload.remote_port = remotePort;
            } else {
                if (!subdomain) {
                    showAlert('Subdomain is required for HTTP/HTTPS tunnels', 'error');
                    return;
                }
                payload.subdomain = subdomain;
            }

            try {
                const res = await fetch('/api/tunnels', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                if (res.status === 401) {
                    showLogin();
                    return;
                }

                if (res.ok) {
                    showAlert('Tunnel created successfully', 'success');
                    toggleCreateForm();
                    document.getElementById('tunnelName').value = '';
                    document.getElementById('tunnelLocalPort').value = '';
                    document.getElementById('tunnelSubdomain').value = '';
                    document.getElementById('tunnelRemotePort').value = '';
                    loadTunnels();
                } else {
                    const error = await res.json();
                    showAlert(error.detail || 'Failed to create tunnel', 'error');
                }
            } catch (e) {
                showAlert('Network error', 'error');
            }
        }

        async function deleteTunnel(id) {
            if (!confirm('Are you sure you want to delete this tunnel?')) return;

            try {
                const res = await fetch('/api/tunnels/' + id, {method: 'DELETE'});

                if (res.status === 401) {
                    showLogin();
                    return;
                }

                if (res.ok) {
                    showAlert('Tunnel deleted', 'success');
                    loadTunnels();
                } else {
                    const error = await res.json();
                    showAlert(error.detail || 'Failed to delete tunnel', 'error');
                }
            } catch (e) {
                showAlert('Network error', 'error');
            }
        }

        async function startService() {
            try {
                const res = await fetch('/api/start', {method: 'POST'});
                if (res.ok) {
                    showAlert('Service started', 'success');
                    loadStatus();
                    setTimeout(loadTunnels, 1000);
                } else {
                    const error = await res.json();
                    showAlert(error.detail || 'Failed to start service', 'error');
                }
            } catch (e) {
                showAlert('Network error', 'error');
            }
        }

        async function stopService() {
            try {
                const res = await fetch('/api/stop', {method: 'POST'});
                if (res.ok) {
                    showAlert('Service stopped', 'success');
                    loadStatus();
                    setTimeout(loadTunnels, 1000);
                } else {
                    const error = await res.json();
                    showAlert(error.detail || 'Failed to stop service', 'error');
                }
            } catch (e) {
                showAlert('Network error', 'error');
            }
        }

        async function restartService() {
            try {
                const res = await fetch('/api/restart', {method: 'POST'});
                if (res.ok) {
                    showAlert('Service restarted', 'success');
                    loadStatus();
                    setTimeout(loadTunnels, 1000);
                } else {
                    const error = await res.json();
                    showAlert(error.detail || 'Failed to restart service', 'error');
                }
            } catch (e) {
                showAlert('Network error', 'error');
            }
        }

        function showAlert(message, type) {
            const alertContainer = document.getElementById('alert');
            alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => alertContainer.innerHTML = '', 3000);
        }
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Tunnel Client - Web UI for managing FRP tunnels")
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=3000,
                        help='Port to listen on (default: 3000)')
    args = parser.parse_args()

    logger.info(f"Starting Tunnel Client on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

"""frpc process management service"""

import os
import stat
import signal
import time
import subprocess
from typing import Dict, Any, Optional, List

from ..config import (
    FRPC_CONFIG,
    FRPC_PID_FILE,
    FRPC_LOG_FILE,
    FRPC_BINARY,
    DEFAULT_FRP_PORT,
    get_logger,
)
from .credentials import get_credentials, get_api_headers
from .api_client import fetch_tunnels, update_all_tunnels_status

logger = get_logger(__name__)


def get_frpc_status() -> Dict[str, Any]:
    """Check if frpc is running"""
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


def regenerate_frpc_config() -> bool:
    """Generate frpc.ini from server tunnels"""
    creds = get_credentials()
    if not creds:
        logger.error("No credentials - cannot generate frpc config")
        return False

    # Get tunnels from server
    tunnels = fetch_tunnels()
    if tunnels is None:
        logger.error("Failed to fetch tunnels from server")
        return False

    # Parse server URL for frpc config
    server_url = creds["server_url"]
    server_url = server_url.replace("http://", "").replace("https://", "")
    # Remove port (API port) and use FRP port
    if ":" in server_url:
        server_addr = server_url.split(":")[0]
    else:
        server_addr = server_url
    server_port = str(DEFAULT_FRP_PORT)

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
    return True


def start_frpc() -> Dict[str, Any]:
    """Start frpc process

    Returns:
        Dict with 'success' bool and either 'pid' or 'error'
    """
    status = get_frpc_status()
    if status["running"]:
        return {"success": False, "error": "Already running"}

    if not os.path.exists(FRPC_BINARY):
        return {"success": False, "error": f"frpc not found at {FRPC_BINARY}"}

    if not regenerate_frpc_config():
        return {"success": False, "error": "Failed to generate config"}

    try:
        log_file = open(FRPC_LOG_FILE, 'a')

        process = subprocess.Popen(
            [FRPC_BINARY, "-c", FRPC_CONFIG],
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )

        with open(FRPC_PID_FILE, 'w') as f:
            f.write(str(process.pid))
        os.chmod(FRPC_PID_FILE, stat.S_IRUSR | stat.S_IWUSR)

        logger.info(f"frpc started with PID {process.pid}")

        # Update tunnel status on server
        update_all_tunnels_status(True)

        return {"success": True, "pid": process.pid}
    except FileNotFoundError:
        return {"success": False, "error": "frpc executable not found"}
    except PermissionError as e:
        return {"success": False, "error": f"Permission denied: {e}"}
    except Exception as e:
        logger.error(f"Failed to start frpc: {e}")
        return {"success": False, "error": str(e)}


def stop_frpc() -> Dict[str, Any]:
    """Stop frpc process

    Returns:
        Dict with 'success' bool and optional 'error'
    """
    status = get_frpc_status()
    if not status["running"]:
        return {"success": False, "error": "Not running"}

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
        update_all_tunnels_status(False)

        return {"success": True}
    except ProcessLookupError:
        try:
            os.remove(FRPC_PID_FILE)
        except FileNotFoundError:
            pass
        update_all_tunnels_status(False)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to stop frpc: {e}")
        return {"success": False, "error": str(e)}


def auto_start_frpc() -> bool:
    """Auto-start frpc if credentials and tunnels exist

    This is called on application startup.
    """
    creds = get_credentials()
    if not creds:
        logger.info("No credentials found - login required")
        return False

    logger.info(f"Loaded credentials for {creds.get('user_email', 'unknown')}")

    # Check if frpc binary exists
    if not os.path.exists(FRPC_BINARY):
        logger.warning(f"frpc not found at {FRPC_BINARY} - service start will fail")
        return False

    logger.info(f"frpc found at {FRPC_BINARY}")

    # Check if already running
    status = get_frpc_status()
    if status["running"]:
        logger.info(f"frpc already running with PID {status['pid']}")
        return True

    # Clean up stale PID file
    if os.path.exists(FRPC_PID_FILE):
        logger.info("Cleaning up stale PID file")
        try:
            os.remove(FRPC_PID_FILE)
        except FileNotFoundError:
            pass

    # Check if there are tunnels to connect
    tunnels = fetch_tunnels()
    if not tunnels:
        logger.info("No tunnels configured - skipping auto-start")
        return False

    logger.info(f"Auto-starting frpc with {len(tunnels)} tunnel(s)...")
    result = start_frpc()

    if result["success"]:
        logger.info(f"Auto-started frpc with PID {result['pid']}")
        return True
    else:
        logger.warning(f"Auto-start frpc failed: {result.get('error')}")
        return False

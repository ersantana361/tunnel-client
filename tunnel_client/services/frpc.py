"""frpc service - config generation and admin API client"""

import json
import os
import stat
import requests
from typing import Dict, Any, List

from ..config import (
    FRPC_CONFIG,
    DEFAULT_FRP_PORT,
    TUNNEL_TOKEN,
    FRPC_ADMIN_URL,
    METRICS_PROXY_HOST,
    METRICS_PROXY_PORT,
    get_logger,
)
from .credentials import get_credentials
from .api_client import fetch_tunnels, update_all_tunnels_status

logger = get_logger(__name__)

# Path for tunnel targets mapping (used by metrics-proxy)
TUNNEL_TARGETS_FILE = os.path.join(os.path.dirname(FRPC_CONFIG), "tunnel_targets.json")


def write_tunnel_targets(tunnels: List[Dict[str, Any]]) -> bool:
    """Write tunnel targets mapping file for metrics-proxy

    This file maps tunnel names to their actual local targets,
    allowing the metrics-proxy to forward requests correctly.
    """
    targets = {}
    for tunnel in tunnels:
        name = tunnel.get('name', 'unnamed')
        targets[name] = {
            'host': tunnel.get('local_host', '127.0.0.1'),
            'port': tunnel.get('local_port', 8080)
        }

    try:
        config_dir = os.path.dirname(TUNNEL_TARGETS_FILE)
        os.makedirs(config_dir, exist_ok=True)

        with open(TUNNEL_TARGETS_FILE, 'w') as f:
            json.dump(targets, f, indent=2)

        logger.info(f"Wrote tunnel targets for {len(targets)} tunnel(s)")
        return True
    except Exception as e:
        logger.error(f"Failed to write tunnel targets: {e}")
        return False


def get_frpc_status() -> Dict[str, Any]:
    """Check if frpc container is running and connected via admin API"""
    try:
        resp = requests.get(f"{FRPC_ADMIN_URL}/api/status", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            # frpc returns proxy status info
            return {"running": True, "proxies": data}
        return {"running": False, "error": f"Status code: {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"running": False, "error": "frpc not reachable"}
    except requests.exceptions.Timeout:
        return {"running": False, "error": "frpc timeout"}
    except Exception as e:
        logger.warning(f"Failed to check frpc status: {e}")
        return {"running": False, "error": str(e)}


def regenerate_frpc_config() -> bool:
    """Generate frpc.toml from server tunnels

    For HTTP/HTTPS tunnels, routes through metrics-proxy for request timing.
    TCP tunnels connect directly to local services.
    """
    creds = get_credentials()
    if not creds:
        logger.error("No credentials - cannot generate frpc config")
        return False

    # Get tunnels from server
    tunnels = fetch_tunnels()
    if tunnels is None:
        logger.error("Failed to fetch tunnels from server")
        return False

    # Write tunnel targets for metrics-proxy
    write_tunnel_targets(tunnels)

    # Parse server URL for frpc config
    server_url = creds["server_url"]
    server_url = server_url.replace("http://", "").replace("https://", "")
    # Remove port (API port) and use FRP port
    if ":" in server_url:
        server_addr = server_url.split(":")[0]
    else:
        server_addr = server_url
    server_port = str(DEFAULT_FRP_PORT)

    # Generate TOML config with admin API enabled
    config_content = f"""serverAddr = "{server_addr}"
serverPort = {server_port}
auth.token = "{TUNNEL_TOKEN or creds.get('tunnel_token', '')}"

webServer.addr = "0.0.0.0"
webServer.port = 7400

"""

    for tunnel in tunnels:
        name = tunnel.get('name', 'unnamed')
        tunnel_type = tunnel.get('type', 'http')
        local_port = tunnel.get('local_port', 8080)
        local_host = tunnel.get('local_host', '127.0.0.1')
        subdomain = tunnel.get('subdomain')
        remote_port = tunnel.get('remote_port')

        config_content += f'[[proxies]]\n'
        config_content += f'name = "{name}"\n'
        config_content += f'type = "{tunnel_type}"\n'

        # Route HTTP/HTTPS through metrics-proxy for request timing
        if tunnel_type in ('http', 'https'):
            config_content += f'localIP = "{METRICS_PROXY_HOST}"\n'
            config_content += f'localPort = {METRICS_PROXY_PORT}\n'
            # Add header to identify tunnel in metrics-proxy
            config_content += f'requestHeaders.set.x-tunnel-name = "{name}"\n'
        else:
            # TCP tunnels go direct (no HTTP headers available)
            config_content += f'localIP = "{local_host}"\n'
            config_content += f'localPort = {local_port}\n'

        if subdomain:
            config_content += f'subdomain = "{subdomain}"\n'

        if remote_port:
            config_content += f'remotePort = {remote_port}\n'

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


def reload_frpc() -> Dict[str, Any]:
    """Regenerate config and trigger frpc hot reload via admin API

    Returns:
        Dict with 'success' bool and optional 'error'
    """
    if not regenerate_frpc_config():
        return {"success": False, "error": "Failed to generate config"}

    try:
        resp = requests.get(f"{FRPC_ADMIN_URL}/api/reload", timeout=5)
        if resp.status_code == 200:
            logger.info("frpc config reloaded successfully")
            update_all_tunnels_status(True)
            return {"success": True}
        else:
            error = f"Reload failed with status {resp.status_code}"
            logger.error(error)
            return {"success": False, "error": error}
    except requests.exceptions.ConnectionError:
        error = "frpc not reachable - container may not be running"
        logger.error(error)
        return {"success": False, "error": error}
    except Exception as e:
        logger.error(f"Failed to reload frpc: {e}")
        return {"success": False, "error": str(e)}


# Keep these for backwards compatibility with routers
def start_frpc() -> Dict[str, Any]:
    """Start/reload frpc - generates config and triggers reload"""
    return reload_frpc()


def stop_frpc() -> Dict[str, Any]:
    """Stop is a no-op - frpc container always runs"""
    logger.info("Stop requested - frpc container keeps running (use docker stop if needed)")
    update_all_tunnels_status(False)
    return {"success": True, "message": "Tunnels marked offline (frpc container still running)"}


def init_frpc() -> bool:
    """Initialize frpc config on application startup

    Generates config if credentials exist. frpc container will pick it up.
    """
    creds = get_credentials()
    if not creds:
        logger.info("No credentials found - login required")
        return False

    logger.info(f"Loaded credentials for {creds.get('user_email', 'unknown')}")

    # Check if there are tunnels to connect
    tunnels = fetch_tunnels()
    if not tunnels:
        logger.info("No tunnels configured - skipping config generation")
        return False

    logger.info(f"Generating frpc config for {len(tunnels)} tunnel(s)...")
    if regenerate_frpc_config():
        logger.info("frpc config generated - container will pick it up")
        # Try to trigger reload in case frpc is already running
        try:
            requests.get(f"{FRPC_ADMIN_URL}/api/reload", timeout=2)
            logger.info("Triggered frpc reload")
        except Exception:
            logger.info("frpc not yet reachable - will load config on start")
        return True
    return False


# Alias for backwards compatibility
auto_start_frpc = init_frpc

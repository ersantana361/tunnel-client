"""Server API client for tunnel management"""

import requests
from typing import Optional, Dict, Any, List

from ..config import get_logger
from .credentials import get_credentials, get_api_headers, clear_credentials

logger = get_logger(__name__)


def fetch_tunnels() -> Optional[List[Dict[str, Any]]]:
    """Fetch tunnels from server"""
    creds = get_credentials()
    if not creds:
        return None

    try:
        response = requests.get(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            return None

        if response.status_code != 200:
            logger.error(f"Failed to fetch tunnels: {response.status_code}")
            return None

        return response.json().get("tunnels", [])

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch tunnels: {e}")
        return None


def create_tunnel(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new tunnel on server

    Returns:
        Dict with 'success' bool and either 'data' or 'error' and 'status_code'
    """
    creds = get_credentials()
    if not creds:
        return {"success": False, "error": "Not authenticated", "status_code": 401}

    try:
        response = requests.post(
            f"{creds['server_url']}/api/tunnels",
            headers=get_api_headers(),
            json=payload,
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            return {"success": False, "error": "Session expired", "status_code": 401}

        if response.status_code == 400:
            error = response.json().get("detail", "Invalid tunnel configuration")
            return {"success": False, "error": error, "status_code": 400}

        if response.status_code not in (200, 201):
            try:
                error_data = response.json()
                detail = error_data.get("detail", f"Server returned {response.status_code}")
            except:
                detail = f"Server returned {response.status_code}: {response.text[:200]}"
            return {"success": False, "error": detail, "status_code": response.status_code}

        return {"success": True, "data": response.json()}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Server connection error: {e}", "status_code": 503}


def delete_tunnel(tunnel_id: int) -> Dict[str, Any]:
    """Delete a tunnel from server

    Returns:
        Dict with 'success' bool and optional 'error' and 'status_code'
    """
    creds = get_credentials()
    if not creds:
        return {"success": False, "error": "Not authenticated", "status_code": 401}

    try:
        response = requests.delete(
            f"{creds['server_url']}/api/tunnels/{tunnel_id}",
            headers=get_api_headers(),
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            return {"success": False, "error": "Session expired", "status_code": 401}

        if response.status_code == 404:
            return {"success": False, "error": "Tunnel not found", "status_code": 404}

        if response.status_code != 200:
            return {"success": False, "error": "Failed to delete tunnel", "status_code": response.status_code}

        return {"success": True}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Server connection error: {e}", "status_code": 503}


def update_tunnel_status(tunnel_id: int, is_active: bool) -> bool:
    """Update tunnel status on server"""
    creds = get_credentials()
    if not creds:
        return False

    try:
        requests.put(
            f"{creds['server_url']}/api/tunnels/{tunnel_id}/status",
            headers=get_api_headers(),
            json={"is_active": is_active},
            timeout=5
        )
        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to update tunnel {tunnel_id} status: {e}")
        return False


def update_all_tunnels_status(is_active: bool) -> bool:
    """Update all tunnels status on server"""
    tunnels = fetch_tunnels()
    if not tunnels:
        return False

    for tunnel in tunnels:
        update_tunnel_status(tunnel["id"], is_active)
    return True

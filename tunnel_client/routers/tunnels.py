"""Tunnels router"""

import yaml
import requests
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import Response

from ..models.schemas import TunnelCreateRequest
from ..services.credentials import get_credentials, get_api_headers, clear_credentials
from ..services.api_client import (
    create_tunnel, delete_tunnel,
    fetch_ssh_keys, add_ssh_key, delete_ssh_key, test_ssh_connection,
)
from ..config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["tunnels"])


@router.get("/tunnels")
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


@router.post("/tunnels")
async def create_tunnel_endpoint(request: TunnelCreateRequest):
    """Create a new tunnel on server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Validate type requirements
    if request.type in ("http", "https") and not request.subdomain:
        raise HTTPException(status_code=400, detail="Subdomain is required for HTTP/HTTPS tunnels")
    if request.type == "tcp" and not request.remote_port:
        raise HTTPException(status_code=400, detail="Remote port is required for TCP tunnels")
    if request.type == "ssh":
        if not request.remote_port:
            raise HTTPException(status_code=400, detail="Remote port is required for SSH tunnels")
        if not request.ssh_user:
            raise HTTPException(status_code=400, detail="SSH user is required for SSH tunnels")

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
    if request.ssh_user:
        payload["ssh_user"] = request.ssh_user

    result = create_tunnel(payload)

    if not result["success"]:
        raise HTTPException(status_code=result["status_code"], detail=result["error"])

    return result["data"]


@router.delete("/tunnels/{tunnel_id}")
async def delete_tunnel_endpoint(tunnel_id: int):
    """Delete a tunnel from server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = delete_tunnel(tunnel_id)

    if not result["success"]:
        raise HTTPException(status_code=result["status_code"], detail=result["error"])

    return {"message": "Tunnel deleted successfully"}


@router.put("/tunnels/{tunnel_id}")
async def update_tunnel_endpoint(tunnel_id: int, request: TunnelCreateRequest):
    """Update a tunnel on server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

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
    if request.ssh_user:
        payload["ssh_user"] = request.ssh_user

    try:
        response = requests.put(
            f"{creds['server_url']}/api/tunnels/{tunnel_id}",
            headers=get_api_headers(),
            json=payload,
            timeout=10
        )

        if response.status_code == 401:
            clear_credentials()
            raise HTTPException(status_code=401, detail="Session expired")

        if response.status_code not in (200, 201):
            try:
                detail = response.json().get("detail", f"Server returned {response.status_code}")
            except:
                detail = f"Server returned {response.status_code}"
            raise HTTPException(status_code=response.status_code, detail=detail)

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


@router.get("/tunnels/export")
async def export_tunnels():
    """Export all tunnels as YAML"""
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

        data = response.json()
        tunnels = data.get("tunnels", [])

        # Strip server-specific fields, keep only importable fields
        export_data = []
        for t in tunnels:
            tunnel_export = {
                "name": t["name"],
                "type": t["type"],
                "local_port": t["local_port"],
                "local_host": t.get("local_host", "127.0.0.1")
            }
            if t.get("subdomain"):
                tunnel_export["subdomain"] = t["subdomain"]
            if t.get("remote_port"):
                tunnel_export["remote_port"] = t["remote_port"]
            if t.get("ssh_user"):
                tunnel_export["ssh_user"] = t["ssh_user"]
            export_data.append(tunnel_export)

        yaml_content = yaml.dump({"tunnels": export_data}, default_flow_style=False, sort_keys=False)
        return Response(content=yaml_content, media_type="application/x-yaml")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


@router.post("/tunnels/import")
async def import_tunnels(body: str = Body(..., media_type="application/x-yaml")):
    """Import tunnels from YAML"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        data = yaml.safe_load(body) or {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    tunnels = data.get("tunnels", [])
    if not tunnels:
        raise HTTPException(status_code=400, detail="No tunnels found in YAML")

    results = {"created": [], "failed": []}

    for tunnel in tunnels:
        name = tunnel.get("name", "unknown")
        tunnel_type = tunnel.get("type")
        local_port = tunnel.get("local_port")
        local_host = tunnel.get("local_host", "127.0.0.1")
        subdomain = tunnel.get("subdomain")
        remote_port = tunnel.get("remote_port")
        ssh_user = tunnel.get("ssh_user")

        # Validate required fields
        if not all([name, tunnel_type, local_port]):
            results["failed"].append({
                "name": name,
                "error": "Missing required fields (name, type, local_port)"
            })
            continue

        # Validate type requirements
        if tunnel_type in ("http", "https") and not subdomain:
            results["failed"].append({
                "name": name,
                "error": "Subdomain is required for HTTP/HTTPS tunnels"
            })
            continue
        if tunnel_type == "tcp" and not remote_port:
            results["failed"].append({
                "name": name,
                "error": "Remote port is required for TCP tunnels"
            })
            continue
        if tunnel_type == "ssh" and (not remote_port or not ssh_user):
            results["failed"].append({
                "name": name,
                "error": "Remote port and SSH user are required for SSH tunnels"
            })
            continue

        payload = {
            "name": name,
            "type": tunnel_type,
            "local_port": local_port,
            "local_host": local_host
        }
        if subdomain:
            payload["subdomain"] = subdomain
        if remote_port:
            payload["remote_port"] = remote_port
        if ssh_user:
            payload["ssh_user"] = ssh_user

        result = create_tunnel(payload)

        if result["success"]:
            results["created"].append(name)
        else:
            results["failed"].append({
                "name": name,
                "error": result.get("error", "Unknown error")
            })

    return results


# ==================== SSH Keys Proxy ====================

@router.get("/ssh-keys")
async def list_ssh_keys():
    """Get SSH keys from server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    keys = fetch_ssh_keys()
    if keys is None:
        raise HTTPException(status_code=503, detail="Failed to fetch SSH keys")

    return {"keys": keys}


@router.post("/ssh-keys")
async def add_ssh_key_endpoint(body: dict = Body(...)):
    """Add an SSH key on server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = add_ssh_key(body)

    if not result["success"]:
        raise HTTPException(status_code=result["status_code"], detail=result["error"])

    return result["data"]


@router.delete("/ssh-keys/{key_id}")
async def delete_ssh_key_endpoint(key_id: int):
    """Delete an SSH key from server"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = delete_ssh_key(key_id)

    if not result["success"]:
        raise HTTPException(status_code=result["status_code"], detail=result["error"])

    return {"message": "SSH key deleted successfully"}


@router.get("/tunnels/{tunnel_id}/test-ssh")
async def test_ssh_endpoint(tunnel_id: int):
    """Test SSH connection for a tunnel"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = test_ssh_connection(tunnel_id)

    if not result["success"]:
        raise HTTPException(status_code=result.get("status_code", 500), detail=result["error"])

    return result["data"]

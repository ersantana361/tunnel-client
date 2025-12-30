"""Tunnels router"""

import requests
from fastapi import APIRouter, HTTPException

from ..models.schemas import TunnelCreateRequest, TunnelImportRequest
from ..services.credentials import get_credentials, get_api_headers, clear_credentials
from ..services.api_client import create_tunnel, delete_tunnel
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
    """Export all tunnels as JSON"""
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
            export_data.append(tunnel_export)

        return {"tunnels": export_data}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Server connection error: {e}")


@router.post("/tunnels/import")
async def import_tunnels(request: TunnelImportRequest):
    """Import tunnels from JSON"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    results = {"created": [], "failed": []}

    for tunnel in request.tunnels:
        # Validate type requirements
        if tunnel.type in ("http", "https") and not tunnel.subdomain:
            results["failed"].append({
                "name": tunnel.name,
                "error": "Subdomain is required for HTTP/HTTPS tunnels"
            })
            continue
        if tunnel.type == "tcp" and not tunnel.remote_port:
            results["failed"].append({
                "name": tunnel.name,
                "error": "Remote port is required for TCP tunnels"
            })
            continue

        payload = {
            "name": tunnel.name,
            "type": tunnel.type,
            "local_port": tunnel.local_port,
            "local_host": tunnel.local_host
        }
        if tunnel.subdomain:
            payload["subdomain"] = tunnel.subdomain
        if tunnel.remote_port:
            payload["remote_port"] = tunnel.remote_port

        result = create_tunnel(payload)

        if result["success"]:
            results["created"].append(tunnel.name)
        else:
            results["failed"].append({
                "name": tunnel.name,
                "error": result.get("error", "Unknown error")
            })

    return results

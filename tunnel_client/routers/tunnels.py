"""Tunnels router"""

import requests
from fastapi import APIRouter, HTTPException

from ..models.schemas import TunnelCreateRequest
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

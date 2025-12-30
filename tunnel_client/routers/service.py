"""Service control router"""

from fastapi import APIRouter, HTTPException

from ..services.credentials import get_credentials
from ..services.frpc import get_frpc_status, start_frpc, stop_frpc, reload_frpc
from ..config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["service"])


@router.get("/status")
async def get_status():
    """Check service status"""
    return get_frpc_status()


@router.post("/start")
async def start_service():
    """Start/reload frpc"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated - please login first")

    result = start_frpc()

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {"message": "Config reloaded"}


@router.post("/stop")
async def stop_service():
    """Mark tunnels offline (frpc container keeps running)"""
    result = stop_frpc()
    return {"message": result.get("message", "Tunnels marked offline")}


@router.post("/restart")
async def restart_service():
    """Reload frpc config"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated - please login first")

    result = reload_frpc()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {"message": "Config reloaded"}

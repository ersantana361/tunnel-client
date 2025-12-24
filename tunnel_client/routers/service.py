"""Service control router"""

from fastapi import APIRouter, HTTPException

from ..services.credentials import get_credentials
from ..services.frpc import get_frpc_status, start_frpc, stop_frpc
from ..config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["service"])


@router.get("/status")
async def get_status():
    """Check service status"""
    return get_frpc_status()


@router.post("/start")
async def start_service():
    """Start frpc"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated - please login first")

    result = start_frpc()

    if not result["success"]:
        if result["error"] == "Already running":
            raise HTTPException(status_code=400, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])

    return {"message": "Service started", "pid": result["pid"]}


@router.post("/stop")
async def stop_service():
    """Stop frpc"""
    result = stop_frpc()

    if not result["success"]:
        if result["error"] == "Not running":
            raise HTTPException(status_code=400, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])

    return {"message": "Service stopped"}


@router.post("/restart")
async def restart_service():
    """Restart frpc"""
    status = get_frpc_status()
    if status["running"]:
        stop_result = stop_frpc()
        if not stop_result["success"] and stop_result["error"] != "Not running":
            raise HTTPException(status_code=500, detail=stop_result["error"])

    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated - please login first")

    start_result = start_frpc()
    if not start_result["success"]:
        raise HTTPException(status_code=500, detail=start_result["error"])

    return {"message": "Service restarted"}

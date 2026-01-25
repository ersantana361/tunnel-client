"""Authentication router"""

import asyncio
import requests
from fastapi import APIRouter, HTTPException

from ..models.schemas import LoginRequest
from ..services.credentials import (
    save_credentials,
    clear_credentials,
    get_credentials,
)
from ..services.frpc import stop_frpc, get_frpc_status, start_frpc
from ..config import get_logger, SERVER_URL

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/config")
async def get_config():
    """Get client configuration (for UI)"""
    return {
        "server_url": SERVER_URL if SERVER_URL else None,
        "server_configured": bool(SERVER_URL)
    }


@router.post("/login")
async def login(request: LoginRequest):
    """Login to tunnel server"""
    # Use configured SERVER_URL if not provided in request
    server_url = request.server_url or SERVER_URL

    if not server_url:
        raise HTTPException(status_code=400, detail="Server URL is required")

    server_url = server_url.rstrip('/')

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
                        asyncio.create_task(_auto_start_after_login())
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


async def _auto_start_after_login():
    """Auto-start frpc after login"""
    try:
        status = get_frpc_status()
        if not status["running"]:
            logger.info("Auto-starting frpc service after login...")
            result = start_frpc()
            if result["success"]:
                logger.info(f"Auto-started frpc with PID {result['pid']}")
            else:
                logger.warning(f"Auto-start failed: {result.get('error')}")
    except Exception as e:
        logger.warning(f"Auto-start failed: {e}")


@router.post("/logout")
async def logout():
    """Logout and clear credentials"""
    # Stop frpc if running
    status = get_frpc_status()
    if status["running"]:
        stop_frpc()

    clear_credentials()
    return {"message": "Logged out successfully"}


@router.get("/auth/status")
async def auth_status():
    """Get authentication status, validating token with remote server"""
    creds = get_credentials()
    if not creds:
        return {
            "authenticated": False,
            "email": None,
            "server_url": None
        }

    # Validate token with remote server
    try:
        response = requests.get(
            f"{creds['server_url']}/api/tunnels",
            headers={"Authorization": f"Bearer {creds['access_token']}"},
            timeout=5
        )
        if response.status_code == 401:
            # Token expired, clear credentials
            logger.info("Access token expired, clearing credentials")
            clear_credentials()
            return {
                "authenticated": False,
                "email": None,
                "server_url": None
            }
    except requests.exceptions.RequestException as e:
        # Server unreachable - still show as authenticated so user can see UI
        # They'll get a proper error when they try to load tunnels
        logger.warning(f"Could not validate token with server: {e}")

    return {
        "authenticated": True,
        "email": creds.get("user_email"),
        "server_url": creds.get("server_url")
    }

"""Metrics router - API endpoints for fetching metrics from server"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.credentials import get_credentials
from ..services.metrics import (
    fetch_metrics,
    fetch_metrics_summary,
    fetch_tunnels_metrics,
)
from ..config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _check_auth():
    """Check if user is authenticated"""
    creds = get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return creds


@router.get("")
async def get_metrics(
    tunnel_name: Optional[str] = Query(None, description="Filter by tunnel name"),
    min_response_time: Optional[int] = Query(None, description="Min response time in ms"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """Get request metrics from server

    Returns list of individual request metrics with timing data.
    """
    _check_auth()

    result = fetch_metrics(
        tunnel_name=tunnel_name,
        min_response_time=min_response_time,
        status_code=status_code,
        limit=limit,
        offset=offset
    )

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Failed to fetch metrics from server"
        )

    return result


@router.get("/summary")
async def get_metrics_summary(
    tunnel_name: Optional[str] = Query(None, description="Filter by tunnel name"),
    period: str = Query("1h", regex="^(1h|24h|7d)$", description="Time period")
):
    """Get aggregated metrics summary

    Returns statistics like avg/p95 response time, total requests,
    bytes transferred, and status code breakdown.
    """
    _check_auth()

    result = fetch_metrics_summary(tunnel_name=tunnel_name, period=period)

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Failed to fetch metrics summary from server"
        )

    return result


@router.get("/tunnels")
async def get_tunnels_metrics():
    """Get metrics summary for all tunnels

    Returns a list of all tunnels with their recent metrics.
    """
    _check_auth()

    result = fetch_tunnels_metrics()

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Failed to fetch tunnel metrics from server"
        )

    return {"tunnels": result}

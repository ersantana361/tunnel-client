"""Metrics service - fetches metrics from tunnel server"""

import requests
from typing import Dict, Any, Optional, List

from ..config import get_logger
from .credentials import get_credentials

logger = get_logger(__name__)


def _get_auth_headers() -> Optional[Dict[str, str]]:
    """Get authorization headers from credentials"""
    creds = get_credentials()
    if not creds or 'access_token' not in creds:
        return None
    return {"Authorization": f"Bearer {creds['access_token']}"}


def _get_server_url() -> Optional[str]:
    """Get server URL from credentials"""
    creds = get_credentials()
    if not creds or 'server_url' not in creds:
        return None
    return creds['server_url']


def fetch_metrics(
    tunnel_name: Optional[str] = None,
    min_response_time: Optional[int] = None,
    status_code: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Optional[Dict[str, Any]]:
    """Fetch metrics from tunnel server

    Args:
        tunnel_name: Filter by tunnel name
        min_response_time: Only show requests slower than N ms
        status_code: Filter by HTTP status code
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Dict with metrics list and pagination info, or None on error
    """
    server_url = _get_server_url()
    headers = _get_auth_headers()

    if not server_url or not headers:
        logger.warning("Cannot fetch metrics: not authenticated")
        return None

    params = {"limit": limit, "offset": offset}
    if tunnel_name:
        params["tunnel_name"] = tunnel_name
    if min_response_time:
        params["min_response_time"] = min_response_time
    if status_code:
        params["status_code"] = status_code

    try:
        resp = requests.get(
            f"{server_url}/api/metrics",
            params=params,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            logger.warning("Metrics fetch failed: unauthorized")
            return None
        else:
            logger.warning(f"Metrics fetch failed: HTTP {resp.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.warning("Metrics fetch timed out")
        return None
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return None


def fetch_metrics_summary(
    tunnel_name: Optional[str] = None,
    period: str = "1h"
) -> Optional[Dict[str, Any]]:
    """Fetch aggregated metrics summary from tunnel server

    Args:
        tunnel_name: Filter by tunnel name (all if None)
        period: Time window - "1h", "24h", or "7d"

    Returns:
        Dict with summary stats, or None on error
    """
    server_url = _get_server_url()
    headers = _get_auth_headers()

    if not server_url or not headers:
        logger.warning("Cannot fetch metrics summary: not authenticated")
        return None

    params = {"period": period}
    if tunnel_name:
        params["tunnel_name"] = tunnel_name

    try:
        resp = requests.get(
            f"{server_url}/api/metrics/summary",
            params=params,
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            logger.warning("Metrics summary fetch failed: unauthorized")
            return None
        else:
            logger.warning(f"Metrics summary fetch failed: HTTP {resp.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.warning("Metrics summary fetch timed out")
        return None
    except Exception as e:
        logger.error(f"Error fetching metrics summary: {e}")
        return None


def fetch_tunnels_metrics() -> Optional[List[Dict[str, Any]]]:
    """Fetch metrics summary for all tunnels

    Returns:
        List of tunnel summaries, or None on error
    """
    server_url = _get_server_url()
    headers = _get_auth_headers()

    if not server_url or not headers:
        logger.warning("Cannot fetch tunnel metrics: not authenticated")
        return None

    try:
        resp = requests.get(
            f"{server_url}/api/metrics/tunnels",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("tunnels", [])
        elif resp.status_code == 401:
            logger.warning("Tunnel metrics fetch failed: unauthorized")
            return None
        else:
            logger.warning(f"Tunnel metrics fetch failed: HTTP {resp.status_code}")
            return None
    except requests.exceptions.Timeout:
        logger.warning("Tunnel metrics fetch timed out")
        return None
    except Exception as e:
        logger.error(f"Error fetching tunnel metrics: {e}")
        return None

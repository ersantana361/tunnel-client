"""Credentials management service"""

import os
import json
import stat
from typing import Optional, Dict, Any

from ..config import CREDENTIALS_FILE, get_logger

logger = get_logger(__name__)

# Global credentials cache
_credentials_cache: Optional[Dict[str, Any]] = None


def load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from file"""
    global _credentials_cache

    if not os.path.exists(CREDENTIALS_FILE):
        return None

    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
        _credentials_cache = creds
        return creds
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load credentials: {e}")
        return None


def save_credentials(server_url: str, access_token: str, tunnel_token: str, user_email: str) -> bool:
    """Save credentials to file"""
    global _credentials_cache

    creds = {
        "server_url": server_url,
        "access_token": access_token,
        "tunnel_token": tunnel_token,
        "user_email": user_email
    }

    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        os.chmod(CREDENTIALS_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        _credentials_cache = creds
        logger.info(f"Credentials saved for {user_email}")
        return True
    except IOError as e:
        logger.error(f"Failed to save credentials: {e}")
        return False


def clear_credentials() -> bool:
    """Clear credentials file"""
    global _credentials_cache

    _credentials_cache = None
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
        logger.info("Credentials cleared")
        return True
    except IOError as e:
        logger.error(f"Failed to clear credentials: {e}")
        return False


def get_credentials() -> Optional[Dict[str, Any]]:
    """Get cached credentials or load from file"""
    global _credentials_cache
    if _credentials_cache is None:
        load_credentials()
    return _credentials_cache


def get_api_headers() -> Dict[str, str]:
    """Get headers for API requests"""
    creds = get_credentials()
    if not creds:
        return {}
    return {
        "Authorization": f"Bearer {creds['access_token']}",
        "Content-Type": "application/json"
    }

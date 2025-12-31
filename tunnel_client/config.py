"""Configuration settings and logging setup"""

import logging
import os

# File paths
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "credentials.json")
FRPC_CONFIG = os.environ.get("FRPC_CONFIG", "/etc/frp/frpc.toml")

# Server settings
SERVER_URL = os.environ.get("SERVER_URL", "")  # Pre-configured server URL
TUNNEL_TOKEN = os.environ.get("TUNNEL_TOKEN", "")  # Override tunnel token from credentials
DEFAULT_FRP_PORT = 7000

# frpc admin API (for hot reload)
FRPC_ADMIN_URL = os.environ.get("FRPC_ADMIN_URL", "http://frpc:7400")

# Metrics proxy settings (for per-request timing)
METRICS_PROXY_HOST = os.environ.get("METRICS_PROXY_HOST", "metrics-proxy")
METRICS_PROXY_PORT = int(os.environ.get("METRICS_PROXY_PORT", "8080"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(name)

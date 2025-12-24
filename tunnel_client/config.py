"""Configuration settings and logging setup"""

import logging
import os

# File paths
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "credentials.json")
FRPC_CONFIG = os.environ.get("FRPC_CONFIG", "/etc/frp/frpc.ini")
FRPC_PID_FILE = os.environ.get("FRPC_PID_FILE", "/tmp/frpc.pid")
FRPC_LOG_FILE = os.environ.get("FRPC_LOG_FILE", "/tmp/frpc.log")
FRPC_BINARY = os.environ.get("FRPC_BINARY", "/usr/local/bin/frpc")

# Server settings
SERVER_URL = os.environ.get("SERVER_URL", "")  # Pre-configured server URL
DEFAULT_FRP_PORT = 7000

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(name)

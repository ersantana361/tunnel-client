"""Pydantic request/response models"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class LoginRequest(BaseModel):
    """Login request model"""
    server_url: Optional[str] = None  # Optional if SERVER_URL is configured
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TunnelCreateRequest(BaseModel):
    """Create tunnel request model"""
    name: str = Field(..., min_length=1, max_length=50)
    type: Literal["http", "https", "tcp", "ssh"]
    local_port: int = Field(..., ge=1, le=65535)
    local_host: str = "127.0.0.1"
    subdomain: Optional[str] = None
    remote_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_user: Optional[str] = None

#!/usr/bin/env python3
"""
Tunnel Client - Web UI for managing FRP tunnels
Main entry point
"""

import argparse
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import get_logger
from .routers import auth_router, tunnels_router, service_router
from .services.frpc import auto_start_frpc

logger = get_logger(__name__)

# Get the package directory for static files
PACKAGE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting Tunnel Client...")
    auto_start_frpc()

    yield

    # Shutdown
    logger.info("Shutting down Tunnel Client")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(title="Tunnel Client", lifespan=lifespan)

    # Mount static files
    static_dir = PACKAGE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    app.include_router(auth_router)
    app.include_router(tunnels_router)
    app.include_router(service_router)

    # Serve index.html at root
    @app.get("/")
    async def root():
        template_path = PACKAGE_DIR / "templates" / "index.html"
        return FileResponse(str(template_path))

    return app


# Create the app instance
app = create_app()


def main():
    """CLI entry point"""
    import uvicorn

    parser = argparse.ArgumentParser(description="Tunnel Client - Web UI for managing FRP tunnels")
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=3000,
                        help='Port to listen on (default: 3000)')
    args = parser.parse_args()

    logger.info(f"Starting Tunnel Client on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

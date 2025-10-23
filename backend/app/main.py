"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app import __version__

app = FastAPI(
    title="Zammad-Kimai Time Tracking Sync",
    description="Synchronization service for time tracking between Zammad and Kimai",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__
    }


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Zammad-Kimai Time Tracking Sync API",
        "version": __version__,
        "docs": "/api/docs"
    }


# API routers will be added here as we build them
# from app.api import auth, connectors, mappings, sync, conflicts, audit, webhook
# app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
# app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
# app.include_router(mappings.router, prefix="/api/mappings", tags=["mappings"])
# app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
# app.include_router(conflicts.router, prefix="/api/conflicts", tags=["conflicts"])
# app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
# app.include_router(webhook.router, prefix="/api/webhook", tags=["webhook"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

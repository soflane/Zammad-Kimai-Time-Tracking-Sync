"""Main FastAPI application."""

import logging

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1.api import api_router
from app.config import settings
from app import __version__
from app.auth import create_access_token, authenticate_user, get_current_active_user
from app.schemas.auth import Token, User

# Custom TRACE level
logging.TRACE = 5
logging.addLevelName(logging.TRACE, "TRACE")

# Add trace method to standard Logger class for all instances
def trace_method(self, msg, *args, **kwargs):
    if self.isEnabledFor(logging.TRACE):
        self._log(logging.TRACE, msg, args, **kwargs)

logging.Logger.trace = trace_method

# Configure root logger early
log_level_str = settings.log_level.upper()
log_level = logging.TRACE if log_level_str == "TRACE" else getattr(logging, log_level_str, logging.INFO)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)-8s - %(message)s'
    )

    root = logging.getLogger()

    # Handle VERBOSE mode and set specific loggers
    if log_level_str == "VERBOSE":
        root_level = logging.DEBUG
        httpcore_level = logging.DEBUG
        httpx_level = logging.DEBUG
        connectors_level = logging.TRACE
        sync_level = logging.DEBUG
        root.info("VERBOSE mode enabled: HTTP details and connector traces active for debugging.")
    elif log_level_str == "TRACE":
        root_level = logging.TRACE
        httpcore_level = logging.TRACE
        httpx_level = logging.TRACE
        connectors_level = logging.TRACE
        sync_level = logging.TRACE
    else:
        root_level = log_level
        httpcore_level = logging.WARNING
        httpx_level = logging.WARNING
        connectors_level = logging.TRACE if log_level_str == "TRACE" else logging.DEBUG
        sync_level = root_level

    root.setLevel(root_level)
    logging.getLogger("httpcore").setLevel(httpcore_level)
    logging.getLogger("httpcore.http11").setLevel(httpcore_level)
    logging.getLogger("httpx").setLevel(httpx_level)
    logging.getLogger("app.connectors").setLevel(connectors_level)
    logging.getLogger("app.services.sync_service").setLevel(sync_level)

    root.trace("Trace logging enabled at startup (verbose details).") if log_level_str == "TRACE" else root.debug("Debug logging enabled at startup.")

app = FastAPI(
    title="Zammad-Kimai Time Tracking Sync",
    description="Synchronization service for time tracking between Zammad and Kimai",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

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

app.include_router(api_router, prefix=settings.api_v1_str)

import logging

log = logging.getLogger(__name__)

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Scheduler setup (runs only when main.py executed directly, not in production uvicorn)
if __name__ == "__main__":
    import uvicorn
    from contextlib import asynccontextmanager
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from app.api.v1.endpoints.connectors import CONNECTOR_TYPES
    from app.services.normalizer import NormalizerService
    from app.services.reconciler import ReconciliationService
    from app.services.sync_service import SyncService
    from app.database import get_db
    import logging

    log = logging.getLogger(__name__)

    # Placeholder for SyncService creation
    @asynccontextmanager
    async def get_sync_service_context():
        zammad_config = {"base_url": settings.zammad_base_url, "api_token": settings.zammad_api_token}
        kimai_config = {"base_url": settings.kimai_base_url, "api_token": settings.kimai_api_token, "default_project_id": settings.kimai_default_project_id}
        
        db_gen = get_db()
        db_session = next(db_gen)

        try:
            sync_service = SyncService(
                zammad_connector=CONNECTOR_TYPES["zammad"](zammad_config),
                kimai_connector=CONNECTOR_TYPES["kimai"](kimai_config),
                normalizer_service=NormalizerService(),
                reconciliation_service=ReconciliationService(),
                db=db_session
            )
            yield sync_service
        finally:
            db_session.close()

    async def periodic_sync_task():
        log.info(f"Running scheduled sync task at {datetime.now()}...")
        async with get_sync_service_context() as sync_service:
            today = datetime.now()
            thirty_days_ago = today - timedelta(days=30)
            await sync_service.sync_time_entries(
                thirty_days_ago.strftime("%Y-%m-%d"),
                today.strftime("%Y-%m-%d")
            )

    @app.on_event("startup")
    async def startup_event():
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            periodic_sync_task,
            IntervalTrigger(hours=settings.sync_schedule_hours),
            id="periodic_sync_job"
        )
        scheduler.start()
        log.info(f"Scheduler started. Sync task scheduled every {settings.sync_schedule_hours} hours.")

    @app.on_event("shutdown")
    async def shutdown_event():
        scheduler = AsyncIOScheduler()
        if scheduler.running:
            scheduler.shutdown()
            log.info("Scheduler shut down.")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.log_level.lower())

from fastapi import APIRouter

from app.api.v1.endpoints import auth, connectors, conflicts, mappings, sync, audit_logs, webhook, reconcile, schedule

api_router = APIRouter()
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])
api_router.include_router(mappings.router, prefix="/mappings", tags=["mappings"])
api_router.include_router(reconcile.router, prefix="/reconcile", tags=["reconcile"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
api_router.include_router(auth.router, tags=["auth"])

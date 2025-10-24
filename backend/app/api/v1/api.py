from fastapi import APIRouter

from app.api.v1.endpoints import connectors, conflicts, mappings, sync

api_router = APIRouter()
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])
api_router.include_router(mappings.router, prefix="/mappings", tags=["mappings"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])

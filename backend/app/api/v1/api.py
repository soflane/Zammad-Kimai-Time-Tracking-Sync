from fastapi import APIRouter

from app.api.v1.endpoints import connectors, conflicts

api_router = APIRouter()
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])

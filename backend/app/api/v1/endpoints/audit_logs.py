from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogInDB
from app.schemas.auth import User
from app.auth import get_current_active_user

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit-logs"]
)

@router.get("/", response_model=List[AuditLogInDB])
async def read_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[str] = Query(None, description="Filter created_at >= YYYY-MM-DD"),
    run_id: Optional[int] = Query(None, description="Filter by sync_run_id"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Session = Depends(get_db)
):
    """Retrieve audit logs with optional filters."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        from datetime import datetime
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(f"{start_date}T00:00:00"))
    if run_id:
        query = query.filter(AuditLog.sync_run_id == run_id)
    logs = query.offset(skip).limit(limit).all()
    return logs

@router.get("/{log_id}", response_model=AuditLogInDB)
async def read_audit_log(
    log_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Session = Depends(get_db)
):
    """Retrieve a single audit log by ID."""
    db_log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if db_log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return db_log

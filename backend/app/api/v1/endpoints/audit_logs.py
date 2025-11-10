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
    tags=["audit-logs"]
)

@router.get("/", response_model=List[AuditLogInDB])
async def read_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = Query(None, description="Filter by specific action"),
    action_type: Optional[str] = Query(None, description="Filter by action type: 'access', 'sync', or 'all'"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[str] = Query(None, description="Filter created_at >= YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter created_at <= YYYY-MM-DD"),
    user: Optional[str] = Query(None, description="Filter by username"),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
    db: Session = Depends(get_db)
):
    """Retrieve audit logs with optional filters."""
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    
    # Filter by specific action
    if action:
        query = query.filter(AuditLog.action == action)
    
    # Filter by action type (access vs sync)
    if action_type:
        if action_type == 'access':
            # Access logs: everything NOT starting with 'sync'
            query = query.filter(~AuditLog.action.like('sync%'))
        elif action_type == 'sync':
            # Sync logs: actions starting with 'sync'
            query = query.filter(AuditLog.action.like('sync%'))
        # 'all' or invalid values: no filter
    
    # Filter by IP address
    if ip_address:
        query = query.filter(AuditLog.ip_address == ip_address)
    
    # Filter by date range
    if start_date:
        from datetime import datetime
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(f"{start_date}T00:00:00"))
    if end_date:
        from datetime import datetime
        query = query.filter(AuditLog.created_at <= datetime.fromisoformat(f"{end_date}T23:59:59"))
    
    # Filter by username
    if user:
        query = query.filter(AuditLog.user == user)
    
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

"""Audit logging helper for consistent audit trail creation."""

from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.utils.ip_extractor import get_client_ip, get_user_agent


def create_audit_log(
    db: Session,
    request: Request,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Create audit log entry with automatic IP and user agent extraction.
    
    Args:
        db: Database session
        request: FastAPI Request object (for IP/user-agent extraction)
        action: Action being performed (e.g., 'login_success', 'connector_created')
        entity_type: Type of entity affected (e.g., 'connector', 'mapping')
        entity_id: ID of affected entity
        user: Username performing the action
        details: Additional context as JSON
        
    Returns:
        Created AuditLog instance
        
    Usage:
        In endpoints:
        ```python
        from app.utils.audit_logger import create_audit_log
        
        # Login success
        audit_log = create_audit_log(
            db, request, 
            action="login_success", 
            user=username
        )
        
        # Connector created
        audit_log = create_audit_log(
            db, request,
            action="connector_created",
            entity_type="connector",
            entity_id=connector.id,
            user=current_user.username,
            details={"connector_type": connector.type}
        )
        ```
    """
    # Extract IP address and user agent from request
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Create audit log entry
    audit_log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log

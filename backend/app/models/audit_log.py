"""Audit log model for tracking all system operations."""

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """Audit trail for all system operations."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # 'sync', 'create', 'update', 'delete', 'resolve_conflict'
    entity_type = Column(String(50), nullable=True)  # 'time_entry', 'connector', 'mapping'
    entity_id = Column(Integer, nullable=True)
    
    # User and context
    user = Column(String(100), nullable=True)  # Username who performed action
    details = Column(JSONB, nullable=True)  # Additional context and data
    
    # IP tracking (for web UI access audit)
    ip_address = Column(String(45), nullable=True)  # Client IP (supports IPv6)
    user_agent = Column(String, nullable=True)  # Browser/client user agent
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index('idx_audit_logs_created_at_desc', created_at.desc()),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_ip_created', 'ip_address', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity='{self.entity_type}')>"

"""Conflict model for tracking reconciliation conflicts."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Float, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Conflict(Base):
    """Detected conflicts during reconciliation that require manual resolution."""

    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Related time entry
    time_entry_id = Column(Integer, ForeignKey("time_entries.id"), nullable=True)
    
    # Conflict details
    conflict_type = Column(String(50), nullable=False, index=True)  # 'duplicate', 'mismatch', 'missing'
    zammad_data = Column(JSONB, nullable=True)  # Original Zammad data
    kimai_data = Column(JSONB, nullable=True)  # Existing Kimai data (if any)

    # Rich conflict metadata
    reason_code = Column(String(50), nullable=False, default='OTHER', index=True)
    reason_detail = Column(Text, nullable=True)

    customer_name = Column(Text, nullable=True)
    project_name = Column(Text, nullable=True)
    activity_name = Column(Text, nullable=True)
    ticket_number = Column(Text, nullable=True)
    zammad_created_at = Column(DateTime(timezone=True), nullable=True)
    zammad_entry_date = Column(Date, nullable=True)
    zammad_time_minutes = Column(Float, nullable=True)
    kimai_begin = Column(DateTime(timezone=True), nullable=True)
    kimai_end = Column(DateTime(timezone=True), nullable=True)
    kimai_duration_minutes = Column(Float, nullable=True)
    kimai_id = Column(Integer, nullable=True)
    
    # Resolution
    resolution_status = Column(String(50), default='pending', nullable=False, index=True)  # 'pending', 'resolved', 'ignored'
    resolution_action = Column(String(50), nullable=True)  # 'create', 'update', 'skip'
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    time_entry = relationship("TimeEntry", back_populates="conflicts")

    __table_args__ = (
        Index('idx_conflicts_resolution_status', 'resolution_status'),
        Index('idx_conflicts_reason_code', 'reason_code'),
    )

    def __repr__(self):
        return f"<Conflict(id={self.id}, type='{self.conflict_type}', status='{self.resolution_status}')>"

"""Conflict model for tracking reconciliation conflicts."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
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
    )

    def __repr__(self):
        return f"<Conflict(id={self.id}, type='{self.conflict_type}', status='{self.resolution_status}')>"

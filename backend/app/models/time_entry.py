"""Time entry model for normalized time tracking data."""

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class TimeEntry(Base):
    """Normalized time entry from any source system."""

    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Source information
    connector_id = Column(Integer, ForeignKey("connectors.id"), nullable=False)
    source = Column(String(50), nullable=False, index=True)  # 'zammad' or 'kimai'
    source_id = Column(String(100), nullable=False)  # Original ID from source system
    
    # Ticket/Project information
    ticket_number = Column(String(50), nullable=True, index=True)
    ticket_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    
    # Time tracking
    time_minutes = Column(Numeric(10, 2), nullable=False)
    activity_type_id = Column(Integer, nullable=True)
    activity_name = Column(String(100), nullable=True)
    
    # User information
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(255), nullable=True)
    
    # Temporal information
    entry_date = Column(Date, nullable=False, index=True)
    
    # Sync status
    synced_to_kimai = Column(Boolean, default=False, nullable=False)
    kimai_id = Column(Integer, nullable=True)
    sync_status = Column(String(50), default='pending', nullable=False, index=True)  # 'pending', 'synced', 'error', 'conflict'
    sync_error = Column(Text, nullable=True)
    
    # Additional data
    tags = Column(JSONB, nullable=True)  # For Kimai tags like ['billed:2024-01']
    extra_metadata = Column(JSONB, nullable=True)  # Additional connector-specific data
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    connector = relationship("Connector", back_populates="time_entries")
    conflicts = relationship("Conflict", back_populates="time_entry", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_time_entries_source_source_id', 'source', 'source_id', unique=True),
        Index('idx_time_entries_sync_status', 'sync_status'),
        Index('idx_time_entries_entry_date', 'entry_date'),
    )

    def __repr__(self):
        return f"<TimeEntry(id={self.id}, source='{self.source}', ticket='{self.ticket_number}', minutes={self.time_minutes})>"

"""Sync run model for tracking synchronization executions."""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class SyncRun(Base):
    """Sync execution history and status tracking."""

    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Execution details
    trigger_type = Column(String(50), nullable=False, default='manual')  # 'scheduled', 'manual', 'webhook'
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False)  # 'running', 'completed', 'failed'
    
    # Statistics
    entries_fetched = Column(Integer, default=0, nullable=False)
    entries_synced = Column(Integer, default=0, nullable=False)
    entries_failed = Column(Integer, default=0, nullable=False)
    conflicts_detected = Column(Integer, default=0, nullable=False)
    
    # Error information
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SyncRun(id={self.id}, trigger='{self.trigger_type}', status='{self.status}', synced={self.entries_synced})>"

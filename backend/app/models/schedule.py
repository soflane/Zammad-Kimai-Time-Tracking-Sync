"""Schedule model for periodic sync configuration."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Schedule(Base):
    """Periodic sync schedule configuration."""

    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    cron = Column(String(100), nullable=False)
    timezone = Column(String(50), nullable=False, default='UTC')
    concurrency = Column(String(20), nullable=False, default='skip')  # 'skip' | 'queue'
    notifications = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Schedule(id={self.id}, cron='{self.cron}', enabled={self.enabled})>"

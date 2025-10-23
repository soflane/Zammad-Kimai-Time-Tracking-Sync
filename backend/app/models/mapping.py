"""Activity mapping model for connector type mappings."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class ActivityMapping(Base):
    """Mapping between Zammad activity types and Kimai activities."""

    __tablename__ = "activity_mappings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Zammad activity type
    zammad_type_id = Column(Integer, nullable=False)
    zammad_type_name = Column(String(100), nullable=True)
    
    # Kimai activity
    kimai_activity_id = Column(Integer, nullable=False)
    kimai_activity_name = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('zammad_type_id', 'kimai_activity_id', name='uq_zammad_kimai_mapping'),
    )

    def __repr__(self):
        return f"<ActivityMapping(id={self.id}, zammad={self.zammad_type_name}, kimai={self.kimai_activity_name})>"

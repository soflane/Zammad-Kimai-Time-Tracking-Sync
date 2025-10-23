"""Connector model for external system configurations."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Connector(Base):
    """Connector configuration for external systems (Zammad, Kimai, etc.)."""

    __tablename__ = "connectors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False, index=True)  # 'zammad' or 'kimai'
    base_url = Column(String(255), nullable=False)
    api_token = Column(Text, nullable=False)  # Encrypted
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSONB, nullable=True)  # Connector-specific settings
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    time_entries = relationship("TimeEntry", back_populates="connector", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Connector(id={self.id}, name='{self.name}', type='{self.type}')>"

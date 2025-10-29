from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class KimaiConnectorConfig(BaseModel):
    """Kimai-specific configuration options"""
    use_global_activities: bool = True
    default_project_id: Optional[int] = None
    default_activity_id: Optional[int] = None  # Fallback activity for unmapped Zammad types
    default_country: str = "BE"
    default_currency: str = "EUR"
    default_timezone: str = "Europe/Brussels"

class ConnectorBase(BaseModel):
    name: str
    type: str # e.g., "zammad", "kimai"
    base_url: HttpUrl
    api_token: str # This will be encrypted before storage
    is_active: bool = True
    settings: Optional[Dict[str, Any]] = None # Connector-specific settings

class ConnectorCreate(ConnectorBase):
    pass

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    api_token: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None

class ConnectorInDB(ConnectorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

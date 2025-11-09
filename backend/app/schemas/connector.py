from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class KimaiConnectorConfig(BaseModel):
    """Kimai-specific configuration options"""
    use_global_activities: bool = True
    default_project_id: Optional[int] = None
    default_activity_id: Optional[int] = None  # Fallback activity for unmapped Zammad types
    ignore_unmapped_activities: bool = False  # Ignore unmapped activities during sync (skip instead of conflict)
    default_country: str = "BE"
    default_currency: str = "EUR"
    default_timezone: str = "Europe/Brussels"
    
    # Time rounding configuration (matching Kimai's rounding behavior for better reconciliation)
    rounding_mode: Optional[str] = 'default'  # 'default', 'closest', 'floor', 'ceil'
    round_begin: Optional[int] = 0  # minutes, 0 = disabled
    round_end: Optional[int] = 0    # minutes, 0 = disabled
    round_duration: Optional[int] = 0  # minutes, 0 = disabled
    rounding_days: Optional[List[int]] = [0, 1, 2, 3, 4, 5, 6]  # Days when rounding applies (0=Mon, 6=Sun)

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

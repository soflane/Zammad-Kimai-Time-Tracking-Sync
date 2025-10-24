from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class AuditLogBase(BaseModel):
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogUpdate(BaseModel):
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AuditLogInDB(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

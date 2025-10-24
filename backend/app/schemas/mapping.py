from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class MappingBase(BaseModel):
    zammad_type_id: int
    zammad_type_name: Optional[str] = None
    kimai_activity_id: int
    kimai_activity_name: Optional[str] = None
    is_active: bool = True

class MappingCreate(MappingBase):
    pass

class MappingUpdate(BaseModel):
    zammad_type_id: Optional[int] = None
    zammad_type_name: Optional[str] = None
    kimai_activity_id: Optional[int] = None
    kimai_activity_name: Optional[str] = None
    is_active: Optional[bool] = None

class MappingInDB(MappingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

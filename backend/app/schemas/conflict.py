from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ConflictBase(BaseModel):
    conflict_type: str = Field(..., description="Type of conflict (e.g., 'duplicate', 'mismatch', 'missing')")
    zammad_data: Optional[dict] = Field(None, description="Original Zammad data causing the conflict")
    kimai_data: Optional[dict] = Field(None, description="Existing Kimai data related to the conflict")

class ConflictCreate(ConflictBase):
    time_entry_id: Optional[int] = Field(None, description="ID of the related time entry, if applicable")

class ConflictUpdate(BaseModel):
    resolution_status: Optional[str] = Field(None, description="Status of the conflict resolution ('pending', 'resolved', 'ignored')")
    resolution_action: Optional[str] = Field(None, description="Action taken to resolve the conflict ('create', 'update', 'skip')")
    resolved_by: Optional[str] = Field(None, description="User who resolved the conflict")
    notes: Optional[str] = Field(None, description="Additional notes regarding the resolution")

class ConflictInDB(ConflictBase):
    id: int
    time_entry_id: Optional[int] = Field(None, description="ID of the related time entry, if applicable")
    resolution_status: str
    resolution_action: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

from typing import Optional
from datetime import datetime, date
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Float as SQLFloat
from typing import Union

class ConflictBase(BaseModel):
    conflict_type: str = Field(..., description="Type of conflict (e.g., 'duplicate', 'mismatch', 'missing')")
    zammad_data: Optional[dict] = Field(None, description="Original Zammad data causing the conflict")
    kimai_data: Optional[dict] = Field(None, description="Existing Kimai data related to the conflict")

    # Rich metadata
    reason_code: str = Field(default='OTHER', description="Machine-readable reason code")
    reason_detail: Optional[str] = Field(None, description="Human-readable explanation")

    customer_name: Optional[str] = Field(None, description="Customer/organization name")
    project_name: Optional[str] = Field(None, description="Project name")
    activity_name: Optional[str] = Field(None, description="Activity name")
    ticket_number: Optional[str] = Field(None, description="Zammad ticket number")
    zammad_created_at: Optional[datetime] = Field(None, description="Zammad created timestamp")
    zammad_entry_date: Optional[date] = Field(None, description="Zammad entry date")
    zammad_time_minutes: Optional[float] = Field(None, description="Zammad time in minutes")
    kimai_begin: Optional[datetime] = Field(None, description="Kimai begin timestamp")
    kimai_end: Optional[datetime] = Field(None, description="Kimai end timestamp")
    kimai_duration_minutes: Optional[float] = Field(None, description="Kimai duration in minutes")
    kimai_id: Optional[int] = Field(None, description="Kimai timesheet ID")

class ConflictCreate(ConflictBase):
    time_entry_id: Optional[int] = Field(None, description="ID of the related time entry, if applicable")

class ConflictUpdate(BaseModel):
    resolution_status: Optional[str] = Field(None, description="Status of the conflict resolution ('pending', 'resolved', 'ignored')")
    resolution_action: Optional[str] = Field(None, description="Action taken to resolve the conflict ('create', 'update', 'skip')")
    resolved_by: Optional[str] = Field(None, description="User who resolved the conflict")
    notes: Optional[str] = Field(None, description="Additional notes regarding the resolution")

class BasicConflictInDB(BaseModel):
    id: int
    time_entry_id: Optional[int] = Field(None, description="ID of the related time entry, if applicable")
    conflict_type: str
    zammad_data: Optional[dict] = Field(None, description="Original Zammad data causing the conflict")
    kimai_data: Optional[dict] = Field(None, description="Existing Kimai data related to the conflict")
    resolution_status: str
    resolution_action: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConflictInDB(ConflictBase):
    id: int
    time_entry_id: Optional[int] = Field(None, description="ID of the related time entry, if applicable")
    resolution_status: str
    resolution_action: Optional[str] = Field(None, description="Action taken to resolve the conflict")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    resolved_by: Optional[str] = Field(None, description="User who resolved")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)

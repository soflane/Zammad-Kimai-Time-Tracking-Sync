"""Schedule schemas for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class ScheduleBase(BaseModel):
    """Base schedule schema."""
    
    cron: str = Field(..., min_length=9, max_length=100, description="Cron expression")
    timezone: str = Field(default='UTC', description="Timezone for schedule")
    concurrency: Literal['skip', 'queue'] = Field(default='skip', description="Concurrency policy")
    notifications: bool = Field(default=False, description="Enable notifications")
    enabled: bool = Field(default=True, description="Enable/disable schedule")
    
    @field_validator('cron')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression syntax."""
        try:
            from croniter import croniter
            if not croniter.is_valid(v):
                raise ValueError('Invalid cron expression')
        except ImportError:
            # If croniter not installed, skip validation
            pass
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string."""
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(f'Invalid timezone: {v}')
        return v


class ScheduleResponse(ScheduleBase):
    """Schedule response with computed fields."""
    
    id: int
    next_runs: list[str] = Field(default_factory=list, description="Next 3 run times (ISO format)")
    updated_at: str
    created_at: str
    
    class Config:
        from_attributes = True


class ScheduleUpdate(BaseModel):
    """Schedule update schema - all fields optional."""
    
    cron: str | None = Field(None, min_length=9, max_length=100)
    timezone: str | None = None
    concurrency: Literal['skip', 'queue'] | None = None
    notifications: bool | None = None
    enabled: bool | None = None
    
    @field_validator('cron')
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        """Validate cron expression syntax if provided."""
        if v is None:
            return v
        try:
            from croniter import croniter
            if not croniter.is_valid(v):
                raise ValueError('Invalid cron expression')
        except ImportError:
            pass
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        """Validate timezone string if provided."""
        if v is None:
            return v
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(v)
        except Exception:
            raise ValueError(f'Invalid timezone: {v}')
        return v

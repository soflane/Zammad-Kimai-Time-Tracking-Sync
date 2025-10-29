from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

class TimeEntryNormalized(BaseModel):
    """Normalized Time Entry structure."""
    source_id: str = Field(..., description="Original ID of the time entry in the source system")
    source: str = Field(..., description="Name of the source system (e.g., 'zammad', 'kimai')")
    ticket_number: Optional[str] = Field(None, description="Associated ticket number/identifier")
    ticket_id: Optional[int] = Field(None, description="Numeric ID of the associated ticket")
    ticket_title: Optional[str] = Field(None, description="Title of the associated ticket")
    org_id: Optional[int] = Field(None, description="Organization ID from Zammad")
    org_name: Optional[str] = Field(None, description="Organization name for customer")
    user_emails: List[str] = Field([], description="List of user emails from organization")
    description: str = Field(..., description="Description of the work performed")
    time_minutes: float = Field(..., gt=0, description="Duration of the time entry in minutes")
    activity_type_id: Optional[int] = Field(None, description="ID of the activity type")
    activity_name: Optional[str] = Field(None, description="Name of the activity type")
    user_email: Optional[str] = Field(None, description="Email of the user who logged the time")
    entry_date: str = Field(..., description="Date of the work (YYYY-MM-DD)")
    created_at: Optional[str] = Field(None, description="ISO 8601 timestamp of creation")
    updated_at: Optional[str] = Field(None, description="ISO 8601 timestamp of last update")
    tags: List[str] = Field([], description="List of tags associated with the time entry")

class BaseConnector(ABC):
    """Abstract Base Class for all connectors."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def fetch_time_entries(self, start_date: str, end_date: str) -> List[TimeEntryNormalized]:
        """Fetches time entries from the connected system."""
        pass

    @abstractmethod
    async def create_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Creates a time entry in the connected system."""
        pass

    @abstractmethod
    async def update_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Updates an existing time entry in the connected system."""
        pass

    @abstractmethod
    async def delete_time_entry(self, source_id: str) -> bool:
        """Deletes a time entry from the connected system."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validates the connection to the external system."""
        pass

    @abstractmethod
    async def fetch_activities(self) -> List[Dict[str, Any]]:
        """Fetches available activities/work types from the connected system."""
        pass

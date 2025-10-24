import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.connectors.base import BaseConnector, TimeEntryNormalized
from app.config import settings
# from app.encrypt import decrypt_data  # Assuming an encryption utility for API tokens

log = logging.getLogger(__name__)

class KimaiConnector(BaseConnector):
    """
    Connector for Kimai time tracking system.
    Handles fetching, creating, updating, and deleting time entries in Kimai.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = self.config["base_url"]
        self.api_token = self.config["api_token"] # In a real app, this would be decrypted
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30)
        self.headers = {
            "X-API-TOKEN": self.api_token,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Helper to make authenticated requests to Kimai API."""
        try:
            response = await self.client.request(method, path, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error for {e.request.url}: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            log.error(f"Request error for {e.request.url}: {e}")
            raise

    async def fetch_time_entries(self, start_date: str, end_date: str) -> List[TimeEntryNormalized]:
        """
        Fetches time sheets from Kimai within a given date range.
        """
        params = {
            "begin": start_date,
            "end": end_date,
            "user": "current" # Assuming we fetch for the user associated with the API token
        }
        response_data = await self._request("GET", "/api/timesheets", params=params)
        
        normalized_entries = []
        for entry in response_data:
            # Kimai API often returns dates in ISO format already
            begin_datetime = datetime.fromisoformat(entry["begin"])
            end_datetime = datetime.fromisoformat(entry["end"])
            duration_minutes = (end_datetime - begin_datetime).total_seconds() / 60

            normalized_entries.append(TimeEntryNormalized(
                source_id=str(entry["id"]),
                source="kimai",
                ticket_number=None, # Kimai doesn't inherently have a ticket number field, might be in description/tags
                ticket_id=None,
                description=entry.get("description", ""),
                time_minutes=duration_minutes,
                activity_type_id=entry["activity"]["id"],
                activity_name=entry["activity"]["name"],
                user_email=entry["user"]["email"],
                entry_date=begin_datetime.strftime("%Y-%m-%d"),
                created_at=entry["createdAt"],
                updated_at=entry["updatedAt"],
                tags=entry.get("tags", [])
            ))     
        return normalized_entries


    async def create_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Creates a time entry (timesheet) in Kimai."""
        # Kimai requires begin and end time, project and activity IDs
        if not time_entry.activity_type_id:
            raise ValueError("Kimai time entry creation requires an activity_type_id.")

        # For simplicity, assume a default project or derive it.
        # This will need to be configured/mapped in a real application.
        # For now, let's assume we have a way to get a project_id.
        project_id = self.config.get("default_project_id", 1) # Placeholder: retrieve from config

        begin_dt = datetime.fromisoformat(time_entry.created_at.replace("Z", "+00:00")) # Assuming created_at as begin time
        end_dt = begin_dt + timedelta(minutes=time_entry.time_minutes)

        kimai_payload = {
            "project": project_id,
            "activity": time_entry.activity_type_id,
            "begin": begin_dt.isoformat(sep='T', timespec='seconds'), # HTML5 datetime format
            "end": end_dt.isoformat(sep='T', timespec='seconds'),
            "description": time_entry.description,
            "tags": time_entry.tags,
            "fixedRate": 0, # Assuming no fixed rate
            "hourlyRate": 0, # Assuming no hourly rate in V1 creation
        }

        response_data = await self._request("POST", "/api/timesheets", json=kimai_payload)
        
        created_at_dt = datetime.fromisoformat(response_data.get("createdAt"))
        updated_at_dt = datetime.fromisoformat(response_data.get("updatedAt"))
        begin_kimai_dt = datetime.fromisoformat(response_data["begin"])
        end_kimai_dt = datetime.fromisoformat(response_data["end"])
        duration_minutes = (end_kimai_dt - begin_kimai_dt).total_seconds() / 60

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="kimai",
            ticket_number=time_entry.ticket_number,
            ticket_id=time_entry.ticket_id,
            description=response_data.get("description", ""),
            time_minutes=duration_minutes,
            activity_type_id=response_data["activity"]["id"],
            activity_name=response_data["activity"]["name"],
            user_email=response_data["user"]["email"],
            entry_date=begin_kimai_dt.strftime("%Y-%m-%d"),
            created_at=response_data["createdAt"],
            updated_at=response_data["updatedAt"],
            tags=response_data.get("tags", [])
        )


    async def update_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Updates an existing time entry (timesheet) in Kimai."""
        if not time_entry.source_id or not time_entry.activity_type_id:
            raise ValueError("Kimai time entry update requires source_id and activity_type_id.")

        begin_dt = datetime.fromisoformat(time_entry.created_at.replace("Z", "+00:00"))
        end_dt = begin_dt + timedelta(minutes=time_entry.time_minutes)

        kimai_payload = {
            "activity": time_entry.activity_type_id,
            "begin": begin_dt.isoformat(sep='T', timespec='seconds'),
            "end": end_dt.isoformat(sep='T', timespec='seconds'),
            "description": time_entry.description,
            "tags": time_entry.tags,
        }

        response_data = await self._request("PATCH", f"/api/timesheets/{time_entry.source_id}", json=kimai_payload)

        created_at_dt = datetime.fromisoformat(response_data.get("createdAt"))
        updated_at_dt = datetime.fromisoformat(response_data.get("updatedAt"))
        begin_kimai_dt = datetime.fromisoformat(response_data["begin"])
        end_kimai_dt = datetime.fromisoformat(response_data["end"])
        duration_minutes = (end_kimai_dt - begin_kimai_dt).total_seconds() / 60

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="kimai",
            ticket_number=time_entry.ticket_number,
            ticket_id=time_entry.ticket_id,
            description=response_data.get("description", ""),
            time_minutes=duration_minutes,
            activity_type_id=response_data["activity"]["id"],
            activity_name=response_data["activity"]["name"],
            user_email=response_data["user"]["email"],
            entry_date=begin_kimai_dt.strftime("%Y-%m-%d"),
            created_at=response_data["createdAt"],
            updated_at=response_data["updatedAt"],
            tags=response_data.get("tags", [])
        )


    async def delete_time_entry(self, source_id: str) -> bool:
        """Deletes a time entry (timesheet) from Kimai."""
        await self._request("DELETE", f"/api/timesheets/{source_id}")
        return True

    async def validate_connection(self) -> bool:
        """
        Validates the connection to Kimai by trying a simple API call,
        e.g., fetching current user information.
        """
        try:
            await self._request("GET", "/api/users/me")
            log.info("Kimai connection validated successfully")
            return True
        except Exception as e:
            log.error(f"Kimai connection validation failed: {e}")
            return False

    async def fetch_activities(self) -> List[Dict[str, Any]]:
        """Fetches available activities from Kimai."""
        response_data = await self._request("GET", "/api/activities")
        return [
            {"id": item["id"], "name": item["name"], "project_id": item["project"]} # Kimai activities are linked to projects
            for item in response_data
            if item.get("visible", True) # Only fetch visible activities
        ]

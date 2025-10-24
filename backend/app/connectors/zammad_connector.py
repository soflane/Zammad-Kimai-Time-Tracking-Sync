import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.connectors.base import BaseConnector, TimeEntryNormalized
from app.config import settings
# from app.encrypt import decrypt_data  # Assuming an encryption utility for API tokens

log = logging.getLogger(__name__)

class ZammadConnector(BaseConnector):
    """
    Connector for Zammad ticketing system.
    Handles fetching, creating, updating, and deleting time entries in Zammad.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = self.config["base_url"]
        self.api_token = self.config["api_token"] # In a real app, this would be decrypted
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30)
        self.headers = {
            "Authorization": f"Token token={self.api_token}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Helper to make authenticated requests to Zammad API."""
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
        Fetches time accounting entries from Zammad within a given date range.
        Zammad's API doesn't directly support filtering time_accountings by date.
        We'll fetch time_accountings for each ticket within the range, which might be inefficient
        and should be optimized if Zammad provides better filtering in the future.
        For now, this will serve as a basic implementation.
        """
        # This is a simplification. A more robust solution would involve fetching tickets
        # created/updated in the range and then their time accountings.
        # Zammad API limitation: no direct date filtering for /time_accountings.

        # For demonstration, let's assume we can query time_accountings by user and
        # filter them manually by creation date in application logic if necessary.
        # This example will fetch all relevant time_accountings and filter them after.

        # Let's assume an endpoint or strategy to fetch relevant time_accountings.
        # Given Zammad's API, it's usually tied to a ticket_id.
        # For a full sync, we'd iterate through tickets updated within the range,
        # then fetch time accountings for each.

        # For now, we will simulate fetching some entries.
        # In a real scenario, this would likely involve a complex query or multiple calls.
        # This `fetch_time_entries` implementation cannot be truly implemented
        # without knowing how to get a list of relevant ticket IDs for the date range
        # first, or if Zammad provides a global time_accountings endpoint with date filters.

        # Placeholder for actual implementation:
        log.info(f"Fetching Zammad time entries from {start_date} to {end_date}. (Implementation for fetching from Zammad API needs refinement based on available endpoints)")
        
        # Simulating a list of TimeEntryNormalized objects
        # In actual implementation, parse Zammad API response into TimeEntryNormalized objects
        mock_entries = [
            TimeEntryNormalized(
                source_id="12345",
                source="zammad",
                ticket_number="#1001",
                ticket_id=1001,
                description="Worked on issue #1001",
                time_minutes=60.0,
                activity_type_id=1,
                activity_name="Support",
                user_email="user@example.com",
                entry_date="2024-01-15",
                created_at="2024-01-15T10:00:00Z",
                updated_at="2024-01-15T10:00:00Z",
                tags=["billed:2024-01"]
            ),
            TimeEntryNormalized(
                source_id="12346",
                source="zammad",
                ticket_number="#1002",
                ticket_id=1002,
                description="Investigated bug #1002",
                time_minutes=30.0,
                activity_type_id=2,
                activity_name="Development",
                user_email="user@example.com",
                entry_date="2024-01-16",
                created_at="2024-01-16T11:00:00Z",
                updated_at="2024-01-16T11:00:00Z",
                tags=["billed:2024-01"]
            )
        ]
        return mock_entries

    async def create_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Creates a time entry in Zammad."""
        # Zammad requires a ticket ID to create a time accounting entry
        if not time_entry.ticket_id:
            raise ValueError("Zammad time entry creation requires a ticket_id.")

        zammad_payload = {
            "time_unit": time_entry.time_minutes,
            "type": time_entry.activity_name, # Zammad often uses type name
            "ticket_id": time_entry.ticket_id,
        }
        # Zammad doesn't directly support description for time_accountings,
        # it's usually tied to a ticket article. We might need a separate call for that.
        # For simplicity, we omit description here if Zammad API doesn't allow it.

        response_data = await self._request("POST", f"/api/v1/tickets/{time_entry.ticket_id}/time_accountings", json=zammad_payload)
        # Parse Zammad response into TimeEntryNormalized. Assuming Zammad returns a similar structure.
        created_at_dt = datetime.fromisoformat(response_data.get("created_at").replace("Z", "+00:00"))
        updated_at_dt = datetime.fromisoformat(response_data.get("updated_at").replace("Z", "+00:00"))

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="zammad",
            ticket_id=response_data["ticket_id"],
            description=time_entry.description, # Keep original description from TimeEntryNormalized
            time_minutes=float(response_data["time_unit"]),
            activity_name=response_data.get("type"), # Assuming 'type' is the activity name
            user_email=time_entry.user_email, # Zammad API might not return this directly
            entry_date=created_at_dt.strftime("%Y-%m-%d"),
            created_at=response_data["created_at"],
            updated_at=response_data["updated_at"],
            # Tags typically not supported directly in Zammad time accountings, managed at Kimai side
            tags=time_entry.tags
        )


    async def update_time_entry(self, time_entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Updates an existing time entry in Zammad."""
        if not time_entry.ticket_id or not time_entry.source_id:
            raise ValueError("Zammad time entry update requires ticket_id and source_id.")
        
        zammad_payload = {
            "time_unit": time_entry.time_minutes,
            "type": time_entry.activity_name, # Zammad often uses type name
        }
        # Similar to create, description updates might require different Zammad API calls.

        response_data = await self._request("PUT", f"/api/v1/tickets/{time_entry.ticket_id}/time_accountings/{time_entry.source_id}", json=zammad_payload)
        updated_at_dt = datetime.fromisoformat(response_data.get("updated_at").replace("Z", "+00:00"))

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="zammad",
            ticket_id=response_data["ticket_id"],
            description=time_entry.description, # Keep original description from TimeEntryNormalized
            time_minutes=float(response_data["time_unit"]),
            activity_name=response_data.get("type"),
            user_email=time_entry.user_email,
            entry_date=updated_at_dt.strftime("%Y-%m-%d"),
            created_at=response_data["created_at"],
            updated_at=response_data["updated_at"],
            tags=time_entry.tags
        )


    async def delete_time_entry(self, source_id: str) -> bool:
        """Deletes a time entry from Zammad."""
        # Zammad API for time_accountings usually requires ticket_id for deletion.
        # This method needs to be enhanced to retrieve ticket_id from somewhere or
        # track it alongside source_id in our database.
        # For now, raising an error as it's not a straightforward single call.
        raise NotImplementedError("Zammad time entry deletion is not directly supported by source_id without ticket_id.")


    async def validate_connection(self) -> bool:
        """
        Validates the connection to Zammad by trying to fetch a user or
        making a simple API call.
        """
        try:
            await self._request("GET", "/api/v1/users/me") # Example: Fetch current user
            return True
        except Exception:
            return False

    async def fetch_activities(self) -> List[Dict[str, Any]]:
        """Fetches available activity types from Zammad."""
        # Zammad uses "time_accountings/types" as activity types
        response_data = await self._request("GET", "/api/v1/time_accounting_types")
        return [
            {"id": item["id"], "name": item["name"]}
            for item in response_data
        ]

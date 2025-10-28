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
        """Fetches aggregated time entries from Zammad by ticket, date, and activity."""
        # Fetch all tickets updated/created in the date range
        tickets = await self.fetch_tickets_by_date(start_date, end_date)
        normalized_entries = []
        for ticket in tickets:
            if ticket.get("organization_id"):
                org = await self.fetch_organization(ticket["organization_id"])
                users = await self.fetch_users_by_org(ticket["organization_id"])
            else:
                org = None
                users = []

            # Fetch time accountings for this ticket
            time_accountings = await self.fetch_ticket_time_accountings(ticket["id"], start_date, end_date)
            
            # Group by activity_type_id and entry_date, sum time
            grouped = {}
            for entry in time_accountings:
                date = entry.get("created_at", "").split("T")[0]
                activity_id = entry.get("type_id")
                key = (ticket["id"], date, activity_id)
                if key not in grouped:
                    grouped[key] = {
                        "ticket_id": ticket["id"],
                        "ticket_number": ticket["number"],
                        "ticket_title": ticket["title"],
                        "org_id": ticket.get("organization_id"),
                        "org_name": org["name"] if org else None,
                        "user_emails": [u.get("email") for u in users] if users else [],
                        "activity_type_id": activity_id,
                        "activity_name": entry.get("type", {}).get("name") if isinstance(entry.get("type"), dict) else entry.get("type", ""),
                        "description": entry.get("note", ""),
                        "entry_date": date,
                        "created_at": entry.get("created_at"),
                        "updated_at": entry.get("updated_at"),
                        "total_minutes": 0
                    }
                grouped[key]["total_minutes"] += float(entry.get("time", 0))

            # Convert to normalized entries
            for key, data in grouped.items():
                normalized_entries.append(TimeEntryNormalized(
                    source_id=f"{data['ticket_id']}_{data['activity_type_id']}_{data['entry_date']}",  # Unique ID for aggregated
                    source="zammad",
                    ticket_number=data["ticket_number"],
                    ticket_id=data["ticket_id"],
                    ticket_title=data["ticket_title"],  # Add to model if needed
                    org_id=data["org_id"],
                    org_name=data["org_name"],
                    user_emails=data["user_emails"],
                    description=data["description"],
                    time_minutes=data["total_minutes"],
                    activity_type_id=data["activity_type_id"],
                    activity_name=data["activity_name"],
                    entry_date=data["entry_date"],
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                    tags=[]
                ))

        return normalized_entries

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
        Validates the connection to Zammad by trying to fetch a user and activities.
        """
        try:
            # Basic connection test
            await self._request("GET", "/api/v1/users/me")
            
            # Test activities fetch permissions
            activities = await self.fetch_activities()
            if not activities:
                raise ValueError("Connection successful but no activities available. Check API token permissions for time accounting types.")
            
            return True
        except ValueError:
            raise  # Re-raise ValueError for specific handling
        except Exception:
            return False

    async def fetch_activities(self) -> List[Dict[str, Any]]:
        """Fetches available activity types from Zammad."""
        try:
            # Zammad uses "/api/v1/time_accounting/types" for types
            response_data = await self._request("GET", "/api/v1/time_accounting/types")
            return [
                {"id": item["id"], "name": item["name"]}
                for item in response_data if item.get("active", True)
            ]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log.warning(f"Zammad time accounting types endpoint not found: {e.request.url}. Returning empty activities list.")
                return []
            elif e.response.status_code in [401, 403]:
                log.error(f"Permission error fetching Zammad activities: {e.response.status_code}")
                raise ValueError(f"Insufficient permissions to access time accounting types (status {e.response.status_code}). Please check API token rights.")
            else:
                log.error(f"Error fetching Zammad activities: {e}")
                raise
        except Exception as e:
            log.error(f"Unexpected error fetching Zammad activities: {e}")
            raise

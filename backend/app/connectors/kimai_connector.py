import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.connectors.base import BaseConnector, TimeEntryNormalized
from app.config import settings
from app.utils.encrypt import decrypt_data

log = logging.getLogger(__name__)

class KimaiConnector(BaseConnector):
    """
    Connector for Kimai time tracking system.
    Handles fetching, creating, updating, and deleting time entries in Kimai.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = self.config["base_url"]
        self.api_token = self.config["api_token"]  # Already decrypted by get_connector_instance
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30)
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
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

        begin_dt = datetime.strptime(time_entry.entry_date, '%Y-%m-%d')
        end_dt = begin_dt + timedelta(minutes=time_entry.time_minutes)

        kimai_payload = {
            "project": project_id,
            "activity": time_entry.activity_type_id,
            "begin": begin_dt.strftime('%Y-%m-%dT%H:%M:%S'), # HTML5 local datetime format
            "end": end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
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

        begin_dt = datetime.strptime(time_entry.entry_date, '%Y-%m-%d')
        end_dt = begin_dt + timedelta(minutes=time_entry.time_minutes)

        kimai_payload = {
            "activity": time_entry.activity_type_id,
            "begin": begin_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            "end": end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
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

    async def list_activities(self) -> List[Dict[str, Any]]:
        """
        Fetches available activities from Kimai with configuration-aware fallbacks.
        Returns normalized activity list based on connector settings.
        """
        settings = self.config.get("settings", {})
        use_global_activities = settings.get("use_global_activities", True)
        default_project_id = settings.get("default_project_id")
        
        params = {"visible": "3"}  # visible=3 for all visible activities
        
        try:
            if use_global_activities:
                # Fetch global activities only
                params["globals"] = "1"
                log.info("Fetching global activities from Kimai")
            elif default_project_id:
                # Fetch activities for specific project
                params["project"] = str(default_project_id)
                log.info(f"Fetching activities for project {default_project_id} from Kimai")
            else:
                # Fetch all visible activities (fallback)
                log.info("Fetching all visible activities from Kimai")
            
            response_data = await self._request("GET", "/api/activities", params=params)
            
            # Normalize response
            return [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "project_id": item.get("project"),
                    "is_global": item.get("project") is None
                }
                for item in response_data
            ]
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Kimai: invalid API token")
            elif e.response.status_code == 403:
                raise ValueError("Kimai: insufficient permissions to list activities")
            elif e.response.status_code == 404 and default_project_id:
                raise ValueError(f"Kimai: project not found for default_project_id {default_project_id}")
            else:
                log.error(f"HTTP error fetching activities: {e.response.status_code} - {e.response.text}")
                raise
        except httpx.RequestError as e:
            log.error(f"Request error fetching activities: {e}")
            raise

    async def fetch_activities(self) -> List[Dict[str, Any]]:
        """Fetches available activities from Kimai (legacy method, calls list_activities)."""
        return await self.list_activities()

    async def find_customer(self, term: str) -> Optional[Dict[str, Any]]:
        """
        Finds a customer in Kimai by search term.
        Returns the first match or None.
        """
        try:
            params = {"term": term, "visible": "3"}
            response_data = await self._request("GET", "/api/customers", params=params)
            if response_data and len(response_data) > 0:
                return response_data[0]
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding customer: {e.response.status_code} - {e.response.text}")
            return None

    async def create_customer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new customer in Kimai.
        Required fields: name, country, currency, timezone
        """
        try:
            response_data = await self._request("POST", "/api/customers", json=payload)
            log.info(f"Created Kimai customer: {response_data.get('name')} (ID: {response_data.get('id')})")
            return response_data
        except httpx.HTTPStatusError as e:
            log.error(f"Error creating customer: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to create Kimai customer: {e.response.text}")

    async def find_project(self, customer_id: int, term: str) -> Optional[Dict[str, Any]]:
        """
        Finds a project in Kimai by customer ID and search term.
        Returns the first match or None.
        """
        try:
            params = {"customer": str(customer_id), "visible": "3", "term": term}
            response_data = await self._request("GET", "/api/projects", params=params)
            if response_data and len(response_data) > 0:
                return response_data[0]
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding project: {e.response.status_code} - {e.response.text}")
            return None

    async def create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new project in Kimai.
        Required fields: name, customer
        Recommended: globalActivities=true for easier activity assignment
        """
        try:
            response_data = await self._request("POST", "/api/projects", json=payload)
            log.info(f"Created Kimai project: {response_data.get('name')} (ID: {response_data.get('id')})")
            return response_data
        except httpx.HTTPStatusError as e:
            log.error(f"Error creating project: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to create Kimai project: {e.response.text}")

    async def create_timesheet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a timesheet in Kimai.
        Required fields: project, activity, begin (HTML5 local datetime), duration (seconds)
        """
        try:
            response_data = await self._request("POST", "/api/timesheets", json=payload)
            log.info(f"Created Kimai timesheet (ID: {response_data.get('id')})")
            return response_data
        except httpx.HTTPStatusError as e:
            log.error(f"Error creating timesheet: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to create Kimai timesheet: {e.response.text}")

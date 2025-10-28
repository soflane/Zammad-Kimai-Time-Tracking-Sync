import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

from app.connectors.base import BaseConnector, TimeEntryNormalized
from app.config import settings
from app.utils.encrypt import decrypt_data

log = logging.getLogger(__name__)

class KimaiConnector(BaseConnector):
    """
    Connector for Kimai time tracking system.
    Handles fetching, creating, updating, and deleting time entries in Kimai.
    
    Key fixes:
    - Always uses HTTPS (auto-upgrades HTTP URLs)
    - Follows HTTP redirects (301/308)
    - Uses HTML5 local datetime format for timesheet queries
    - Omits 'user' parameter (defaults to current user)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        raw_base_url = self.config["base_url"]
        self.base_url = self._normalize_base_url(raw_base_url)
        self.api_token = self.config["api_token"]  # Already decrypted by get_connector_instance
        
        # Create client with redirect following and extended timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            follow_redirects=True,  # Handle 301/308 redirects automatically
            timeout=30.0,
            verify=True  # Verify SSL certificates
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        log.info(f"Kimai connector initialized with base URL: {self.base_url}")

    def _normalize_base_url(self, url: str) -> str:
        """
        Normalizes the base URL:
        - Upgrades http:// to https://
        - Removes trailing slashes
        - Validates format
        """
        url = url.strip()
        
        # Auto-upgrade HTTP to HTTPS for Kimai (most instances require it)
        if url.startswith("http://"):
            https_url = url.replace("http://", "https://", 1)
            log.warning(
                f"Kimai base URL uses HTTP. Auto-upgrading to HTTPS: {https_url}\n"
                f"Please update the connector configuration to use HTTPS directly."
            )
            url = https_url
        
        # Ensure it starts with https://
        if not url.startswith("https://"):
            raise ValueError(
                f"Invalid Kimai base URL: {url}\n"
                f"URL must start with https:// (e.g., https://timesheet.ayoute.be)"
            )
        
        # Remove trailing slashes for consistent path joining
        url = url.rstrip("/")
        
        return url

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Helper to make authenticated requests to Kimai API.
        Handles errors with informative messages.
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"
        
        try:
            log.debug(f"Kimai API {method} {self.base_url}{path}")
            response = await self.client.request(method, path, headers=self.headers, **kwargs)
            log.debug(f"Kimai API response: {response.status_code}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            url = str(e.request.url)
            response_text = e.response.text
            
            # Provide helpful error messages based on status code
            if status in (301, 302, 307, 308):
                # Redirect detected (shouldn't happen with follow_redirects=True, but just in case)
                location = e.response.headers.get("Location", "unknown")
                error_msg = (
                    f"Kimai redirected from {url} to {location}.\n"
                    f"Please update the connector base URL to use HTTPS: {location}"
                )
                log.error(error_msg)
                raise ValueError(error_msg)
                
            elif status == 400:
                # Bad request - often due to invalid query parameters
                error_msg = f"Kimai API bad request to {url}: {response_text}\n"
                if "/timesheets" in path and method == "GET":
                    error_msg += (
                        "Hint: Ensure 'begin' and 'end' parameters use HTML5 datetime format "
                        "(e.g., '2025-09-28T00:00:00'). Do not use 'user=current' - omit 'user' "
                        "parameter or use numeric user ID."
                    )
                log.error(error_msg)
                raise ValueError(error_msg)
                
            elif status == 401:
                error_msg = f"Kimai authentication failed: Invalid API token for {url}"
                log.error(error_msg)
                raise ValueError(error_msg)
                
            elif status == 403:
                error_msg = f"Kimai permission denied: Insufficient permissions for {url}"
                log.error(error_msg)
                raise ValueError(error_msg)
                
            elif status == 404:
                error_msg = f"Kimai resource not found: {url}"
                log.error(error_msg)
                raise ValueError(error_msg)
                
            elif status == 422:
                # Unprocessable entity - validation errors
                error_msg = f"Kimai validation error for {url}: {response_text}\n"
                if "/timesheets" in path:
                    error_msg += (
                        "Hint: Check that all required fields are provided and properly formatted. "
                        "Duration should be in seconds, begin/end in HTML5 datetime format."
                    )
                log.error(error_msg)
                raise ValueError(error_msg)
                
            else:
                # Generic HTTP error
                error_msg = f"Kimai HTTP {status} error for {url}: {response_text}"
                log.error(error_msg)
                raise ValueError(error_msg)
                
        except httpx.RequestError as e:
            error_msg = f"Kimai request error for {e.request.url}: {str(e)}"
            log.error(error_msg)
            raise ValueError(error_msg)

    async def fetch_time_entries(self, start_date: str, end_date: str) -> List[TimeEntryNormalized]:
        """
        Fetches time sheets from Kimai within a given date range.
        
        Args:
            start_date: Date string in 'YYYY-MM-DD' format
            end_date: Date string in 'YYYY-MM-DD' format
            
        Note: Kimai requires HTML5 local datetime format for begin/end params.
        The 'user' parameter is omitted to default to the current authenticated user.
        """
        log.info(f"Fetching Kimai time entries for date range: {start_date} to {end_date}")
        # Convert dates to HTML5 local datetime format
        # Start of day for begin, end of day for end
        begin_datetime = f"{start_date}T00:00:00"
        end_datetime = f"{end_date}T23:59:59"
        
        params = {
            "begin": begin_datetime,
            "end": end_datetime,
            # Do NOT include 'user' parameter - defaults to current user
            # Using 'user=current' causes 400 errors (must be numeric ID or 'all')
            "orderBy": "begin",
            "order": "DESC"
        }
        
        log.debug(f"Fetching Kimai timesheets with params: {params}")
        response_data = await self._request("GET", "/api/timesheets", params=params)
        log.info(f"Received {len(response_data)} raw timesheets from Kimai")
        
        normalized_entries = []
        for entry in response_data:
            # Kimai API often returns dates in ISO format already
            begin_datetime = datetime.fromisoformat(entry["begin"])
            end_datetime = datetime.fromisoformat(entry["end"])
            duration_minutes = (end_datetime - begin_datetime).total_seconds() / 60

            normalized = TimeEntryNormalized(
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
            )
            normalized_entries.append(normalized)
            log.debug(f"Normalized Kimai entry {normalized.source_id}: {normalized.description or 'no desc'}, {duration_minutes} min on {normalized.entry_date}, activity {normalized.activity_type_id}")

        log.info(f"Created {len(normalized_entries)} normalized Kimai time entries")
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

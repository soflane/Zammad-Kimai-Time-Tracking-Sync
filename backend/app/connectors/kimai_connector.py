import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

from app.connectors.base import BaseConnector, TimeEntryNormalized
from app.config import settings
from app.utils.encrypt import decrypt_data

log = logging.getLogger(__name__)

def _to_local_html5(dt_str: Optional[str]) -> Optional[str]:
    """
    Convert Kimai ISO-8601 (with or without timezone) to HTML5 local datetime
    'YYYY-MM-DDTHH:MM:SS' (no timezone). Returns None if input is falsy/invalid.
    """
    if not dt_str:
        return None
    try:
        # Kimai returns ISO-8601 with offset, eg. '2025-10-28T13:37:24+01:00'
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None
    # Drop tzinfo -> local naive, keep wall-clock
    return dt.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")

def _seconds_from(begin_local: Optional[str], end_local: Optional[str]) -> int:
    """
    Calculate seconds difference from two HTML5 local datetimes.
    Returns 0 if not computable.
    """
    if not begin_local or not end_local:
        return 0
    try:
        b = datetime.fromisoformat(begin_local)
        e = datetime.fromisoformat(end_local)
        return max(0, int((e - b).total_seconds()))
    except Exception:
        return 0

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
            log.trace(f"Kimai API {method} {self.base_url}{path}")
            response = await self.client.request(method, path, headers=self.headers, **kwargs)
            log.trace(f"Kimai API response: {response.status_code}")
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            url = str(e.request.url)
            response_text = e.response.text
            
            # Try to parse JSON error details for better diagnostics
            error_details = None
            try:
                error_json = e.response.json()
                error_details = error_json
                log.error(f"Kimai API error JSON: {error_json}")
            except Exception:
                pass
            
            # Always log the raw response body
            log.error(f"Kimai API raw response body: {response_text}")
            
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
                # Bad request - often due to invalid query parameters or form validation
                error_msg = f"Kimai API bad request to {url}\n"
                if error_details:
                    error_msg += f"Error details: {error_details}\n"
                error_msg += f"Raw response: {response_text}\n"
                
                if "/timesheets" in path and method == "GET":
                    error_msg += (
                        "Hint: Ensure 'begin' and 'end' parameters use HTML5 datetime format "
                        "(e.g., '2025-09-28T00:00:00'). Do not use 'user=current' - omit 'user' "
                        "parameter or use numeric user ID."
                    )
                elif "/timesheets" in path and method == "POST":
                    error_msg += (
                        "Hint: TimesheetEditForm requires 'begin' and 'end' (not 'duration'). "
                        "Tags must be comma-separated string. Ensure project allows globalActivities."
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
                error_msg = f"Kimai validation error for {url}\n"
                if error_details:
                    error_msg += f"Error details: {error_details}\n"
                error_msg += f"Raw response: {response_text}\n"
                if "/timesheets" in path:
                    error_msg += (
                        "Hint: Check that all required fields are provided and properly formatted. "
                        "Use 'end' instead of 'duration'. Begin/end must be HTML5 datetime format."
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
        params = {
            "begin": f"{start_date}T00:00:00",
            "end": f"{end_date}T23:59:59",
            "orderBy": "begin",
            "order": "DESC",
            "full": "true"  # CRITICAL: Fetch tags and full details
        }
        response_data = await self._request("GET", "/api/timesheets", params=params)
        count = len(response_data) if isinstance(response_data, list) else 0
        log.info(f"Received {count} raw timesheets from Kimai (full=true)")

        normalized: List[TimeEntryNormalized] = []
        for entry in (response_data or []):
            # entry with full=true includes expanded objects
            raw_activity = entry.get("activity")
            raw_project = entry.get("project")
            raw_user    = entry.get("user")

            # Extract IDs from either ints or nested objects
            def _id(x: Any) -> Optional[int]:
                if x is None:
                    return None
                if isinstance(x, int):
                    return x
                if isinstance(x, dict):
                    return x.get("id")
                return None

            begin_local = _to_local_html5(entry.get("begin"))
            end_local   = _to_local_html5(entry.get("end"))

            # Duration in seconds: prefer server-provided, else compute from begin/end
            duration_s = entry.get("duration")
            if duration_s is None:
                duration_s = _seconds_from(begin_local, end_local)
            duration_sec = int(duration_s or 0)

            # Kimai returns actual timestamps with full=true
            created_at = entry.get("begin")  # Use begin as created_at
            updated_at = entry.get("end", created_at)

            # Parse tags - handle both array and string formats
            tags = entry.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, list):
                # Handle both string tags and potential object tags
                parsed_tags = []
                for tag in tags:
                    if isinstance(tag, str):
                        parsed_tags.append(tag)
                    elif isinstance(tag, dict) and "name" in tag:
                        parsed_tags.append(tag["name"])
                tags = parsed_tags
            else:
                tags = []

            # Parse Zammad metadata from tags for matching (idempotency) - legacy support
            parsed_source_id = str(entry.get("id"))  # Default to Kimai ID
            parsed_ticket_number = None
            for tag in tags:
                if tag.startswith("zid:"):
                    parsed_source_id = tag.split("zid:", 1)[1]
                if tag.startswith("ticket:"):
                    parsed_ticket_number = tag.split("ticket:", 1)[1].lstrip("#")

            # Primary: Parse marker from description "ZAM:T{tid}|TA:{ta_id}"
            desc = entry.get("description") or ""
            import re
            marker_match = re.match(r'ZAM:T(\d+)\|TA:(\d+)', desc)
            if marker_match:
                tid, ta_id = marker_match.groups()
                parsed_ticket_number = tid
                parsed_source_id = ta_id
                log.debug(f"Parsed marker from description: ticket={tid}, source_id={ta_id}")

            # Fallback: Parse ticket_number from description if not from marker/tags (legacy support)
            if not parsed_ticket_number:
                ticket_match = re.search(r"Ticket-([#]?\d+)", desc)
                if ticket_match:
                    parsed_ticket_number = ticket_match.group(1).lstrip("#")
                    log.debug(f"Parsed ticket_number '{parsed_ticket_number}' from description: {desc[:50]}...")

            log.debug(f"Normalized Kimai {parsed_source_id}: ticket={parsed_ticket_number}, begin_time={begin_local}")

            entry_date = None
            if begin_local:
                entry_date = begin_local.split("T")[0]

            normalized.append(TimeEntryNormalized(
                source="kimai",
                source_id=parsed_source_id,
                description=desc,
                duration_sec=duration_sec,
                activity_type_id=_id(raw_activity),
                activity_name=None,   # can be hydrated later if needed
                user_email=None,      # user email not in this payload; optional in model
                user_name=None,
                entry_date=entry_date,
                created_at=created_at,
                updated_at=updated_at,
                tags=tags,
                ticket_number=parsed_ticket_number,
                ticket_id=None,
                begin_time=begin_local,
                end_time=end_local,
            ))

        if normalized:
            sample = normalized[0]
            log.debug(
                f"Kimai normalized sample id={sample.source_id} "
                f"begin={sample.created_at} end={sample.updated_at} "
                f"duration_min={(sample.duration_sec // 60)} tags={sample.tags}"
            )
        log.info(f"Kimai fetch normalized {len(normalized)} entries ({params['begin']} → {params['end']}), tags included")
        return normalized


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
        end_dt = begin_dt + timedelta(seconds=time_entry.duration_sec)

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
        duration_sec = int((end_kimai_dt - begin_kimai_dt).total_seconds())

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="kimai",
            ticket_number=time_entry.ticket_number,
            ticket_id=time_entry.ticket_id,
            description=response_data.get("description", ""),
            duration_sec=duration_sec,
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
        end_dt = begin_dt + timedelta(seconds=time_entry.duration_sec)

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
        duration_sec = int((end_kimai_dt - begin_kimai_dt).total_seconds())

        return TimeEntryNormalized(
            source_id=str(response_data["id"]),
            source="kimai",
            ticket_number=time_entry.ticket_number,
            ticket_id=time_entry.ticket_id,
            description=response_data.get("description", ""),
            duration_sec=duration_sec,
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

    async def find_customer_by_number(self, external_number: str) -> Optional[Dict[str, Any]]:
        """
        Finds a customer in Kimai by exact number match (external ID).
        Returns the customer if found, None otherwise.
        """
        try:
            params = {"term": external_number, "visible": "3"}
            response_data = await self._request("GET", "/api/customers", params=params)
            
            # Filter client-side for exact match on number field
            for customer in (response_data or []):
                if customer.get("number") == external_number:
                    log.debug(f"Found customer by number {external_number}: {customer.get('name')} (ID: {customer.get('id')})")
                    return customer
            
            log.debug(f"No customer found with exact number: {external_number}")
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding customer by number: {e.response.status_code} - {e.response.text}")
            return None

    async def find_customer_by_name_exact(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Finds a customer in Kimai by exact name match (case-insensitive).
        Returns the customer if found, None otherwise.
        """
        try:
            params = {"term": name, "visible": "3"}
            response_data = await self._request("GET", "/api/customers", params=params)
            
            # Filter client-side for exact match (case-insensitive)
            name_lower = name.lower()
            for customer in (response_data or []):
                if customer.get("name", "").lower() == name_lower:
                    log.debug(f"Found customer by exact name '{name}': ID {customer.get('id')}")
                    return customer
            
            log.debug(f"No customer found with exact name: {name}")
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding customer by name: {e.response.status_code} - {e.response.text}")
            return None

    async def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """
        Fetches a customer by ID from Kimai.
        
        Args:
            customer_id: The customer ID to fetch
            
        Returns:
            Customer object with all details
        """
        try:
            response_data = await self._request("GET", f"/api/customers/{customer_id}")
            log.debug(f"Fetched customer {customer_id}: {response_data.get('name')}")
            return response_data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log.error(f"Customer {customer_id} not found")
                raise ValueError(f"Kimai customer {customer_id} does not exist")
            log.error(f"Error fetching customer {customer_id}: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to fetch Kimai customer {customer_id}: {e.response.text}")

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
            log.debug(f"Kimai create_project payload: {payload}")
            response_data = await self._request("POST", "/api/projects", json=payload)
            log.info(f"Created Kimai project: {response_data.get('name')} (ID: {response_data.get('id')})")
            return response_data
        except (httpx.HTTPStatusError, ValueError) as e:
            error_msg = str(e)
            log.error(f"Error creating project with payload {payload}")
            log.error(f"Error details: {error_msg}")
            # Re-raise the ValueError that _request() already formatted
            raise

    async def get_project(self, project_id: int) -> Dict[str, Any]:
        """
        Fetches a project by ID from Kimai.
        
        Args:
            project_id: The project ID to fetch
            
        Returns:
            Project object with all details including globalActivities flag
        """
        try:
            response_data = await self._request("GET", f"/api/projects/{project_id}")
            log.debug(f"Fetched project {project_id}: globalActivities={response_data.get('globalActivities')}")
            return response_data
        except httpx.HTTPStatusError as e:
            log.error(f"Error fetching project {project_id}: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to fetch Kimai project {project_id}: {e.response.text}")

    async def patch_project(self, project_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates an existing project in Kimai.
        
        Args:
            project_id: The project ID to update
            payload: Fields to update (e.g., {"globalActivities": true})
            
        Returns:
            Updated project object
        """
        try:
            response_data = await self._request("PATCH", f"/api/projects/{project_id}", json=payload)
            log.info(f"Updated project {project_id}: {payload}")
            return response_data
        except httpx.HTTPStatusError as e:
            log.error(f"Error updating project {project_id}: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Failed to update Kimai project {project_id}: {e.response.text}")

    async def find_project_by_number(self, customer_id: int, project_number: str) -> Optional[Dict[str, Any]]:
        """
        Finds a project in Kimai by exact number match (external ID).
        Returns the project if found, None otherwise.
        """
        try:
            params = {"customer": str(customer_id), "visible": "3", "term": project_number}
            response_data = await self._request("GET", "/api/projects", params=params)
            
            # Filter client-side for exact match on number field
            for project in (response_data or []):
                if project.get("number") == project_number:
                    log.debug(f"Found project by number {project_number}: {project.get('name')} (ID: {project.get('id')})")
                    return project
            
            log.debug(f"No project found with exact number: {project_number}")
            return None
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding project by number: {e.response.status_code} - {e.response.text}")
            return None

    async def find_timesheet_by_tag_and_range(
        self, 
        tag: str, 
        begin: str, 
        end: str
    ) -> Optional[Dict[str, Any]]:
        """
        Finds a timesheet in Kimai by tag within a date range.
        Used for idempotency checking.
        
        Args:
            tag: Tag to search for (e.g., "zid:123")
            begin: Start datetime in HTML5 format (YYYY-MM-DDTHH:MM:SS)
            end: End datetime in HTML5 format (YYYY-MM-DDTHH:MM:SS)
            
        Returns:
            First matching timesheet or None
        """
        try:
            params = {
                "begin": begin,
                "end": end,
                "full": "true",  # Need tags
                "size": "10"  # Limit results
            }
            
            # Note: Kimai API doesn't support tags[] filter parameter in practice
            # We'll fetch timesheets in the range and filter client-side
            response_data = await self._request("GET", "/api/timesheets", params=params)
            
            # Filter client-side for the specific tag
            for timesheet in (response_data or []):
                tags = timesheet.get("tags") or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                elif isinstance(tags, list):
                    # Handle both string tags and object tags
                    parsed_tags = []
                    for t in tags:
                        if isinstance(t, str):
                            parsed_tags.append(t)
                        elif isinstance(t, dict) and "name" in t:
                            parsed_tags.append(t["name"])
                    tags = parsed_tags
                
                if tag in tags:
                    log.debug(f"Found timesheet with tag '{tag}': ID {timesheet.get('id')}")
                    return timesheet
            
            log.debug(f"No timesheet found with tag '{tag}' in range {begin} to {end}")
            return None
            
        except httpx.HTTPStatusError as e:
            log.error(f"Error finding timesheet by tag: {e.response.status_code} - {e.response.text}")
            return None

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

from typing import List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session # Required for database interaction

import logging

from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.connectors.base import TimeEntryNormalized
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService, ReconciledTimeEntry, ReconciliationStatus
from app.models.conflict import Conflict as DBConflict # Import DB Conflict model
from app.schemas.conflict import ConflictCreate # Import Pydantic schema for creating conflicts
from app.models.mapping import ActivityMapping

log = logging.getLogger(__name__)

import traceback


class SyncService:
    """
    Orchestrates the synchronization of time entries between Zammad and Kimai.
    """

    def __init__(
        self,
        zammad_connector: ZammadConnector,
        kimai_connector: KimaiConnector,
        normalizer_service: NormalizerService,
        reconciliation_service: ReconciliationService,
        db: Session # Inject database session here
    ):
        self.zammad_connector = zammad_connector
        self.kimai_connector = kimai_connector
        self.normalizer_service = normalizer_service
        self.reconciliation_service = reconciliation_service
        self.db = db

    async def sync_time_entries(self, start_date: str, end_date: str) -> dict:
        """
        Performs a full synchronization cycle for time entries within the given date range.
        Returns stats: {'processed': int, 'created': int, 'conflicts': int}
        """
        try:
            log.debug(f"SyncService.sync_time_entries called with period {start_date} to {end_date}")
            log.info(f"=== Starting sync from {start_date} to {end_date} ===")
            
            stats = {
                "processed": 0,
                "created": 0,
                "conflicts": 0,
                "zammad_fetched": 0,
                "kimai_fetched": 0,
                "reconciled_matches": 0,
                "reconciled_missing_kimai": 0,
                "reconciled_conflicts": 0,
                "unmapped": 0
            }

            # 1. Fetch entries from Zammad (already normalized by connector)
            log.debug("Fetching Zammad entries...")
            zammad_normalized_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
            log.debug(f"Zammad entries fetched: {len(zammad_normalized_entries)}")
            
            # Log each entry for debugging
            for entry in zammad_normalized_entries:
                log.debug(f"Zammad entry {entry.source_id}: ticket {entry.ticket_number}, {(entry.duration_sec // 60)} min, activity {entry.activity_type_id}")

            stats["zammad_fetched"] = len(zammad_normalized_entries)
            log.info(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

            # 2. Fetch entries from Kimai (already normalized by connector)
            log.debug("Fetching Kimai entries...")
            kimai_normalized_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
            log.debug(f"Kimai entries fetched: {len(kimai_normalized_entries)}")
            
            # Log each entry for debugging
            for entry in kimai_normalized_entries:
                log.trace(f"Kimai entry {entry.source_id}: {entry.description or 'no desc'}, {(entry.duration_sec // 60)} min")

            stats["kimai_fetched"] = len(kimai_normalized_entries)
            log.info(f"Fetched {len(kimai_normalized_entries)} normalized entries from Kimai.")

            # 3. Reconcile entries
            log.debug("Running reconciliation...")
            reconciled_results = await self.reconciliation_service.reconcile_entries(
                zammad_normalized_entries,
                kimai_normalized_entries
            )
            log.info(f"Reconciliation resulted in {len(reconciled_results)} entries to process.")
            
            # Count reconciliation types
            for result in reconciled_results:
                if result.reconciliation_status == ReconciliationStatus.MATCH:
                    stats["reconciled_matches"] += 1
                    log.debug(f"MATCH found: Zammad {result.zammad_entry.source_id} == Kimai {result.kimai_entry.source_id}")
                elif result.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                    stats["reconciled_missing_kimai"] += 1
                    log.debug(f"MISSING_IN_KIMAI: Zammad {result.zammad_entry.source_id} needs creation")
                elif result.reconciliation_status == ReconciliationStatus.CONFLICT:
                    stats["reconciled_conflicts"] += 1
                    log.debug(f"CONFLICT: Zammad {result.zammad_entry.source_id} vs Kimai {result.kimai_entry.source_id}")
                elif result.reconciliation_status == ReconciliationStatus.MISSING_IN_ZAMMAD:
                    log.debug(f"MISSING_IN_ZAMMAD: Kimai {result.kimai_entry.source_id} (ignoring for one-way sync)")

            # 4. Process reconciled results
            for reconciled_entry in reconciled_results:
                log.debug(f"Processing reconciled entry: {reconciled_entry.reconciliation_status}")
                stats["processed"] += 1
                if reconciled_entry.reconciliation_status == ReconciliationStatus.MATCH:
                    log.debug(f"MATCH: Zammad {reconciled_entry.zammad_entry.source_id} & Kimai {reconciled_entry.kimai_entry.source_id} are in sync.")
                    # Future: Update our DB with association or latest state
                elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                    log.debug(f"MISSING IN KIMAI: Zammad entry {reconciled_entry.zammad_entry.source_id} not found in Kimai. Attempting creation...")
                    zammad_entry = reconciled_entry.zammad_entry
                    
                    # Determine Kimai activity ID
                    kimai_activity_id = None
                    
                    # Try to find activity mapping
                    if zammad_entry.activity_type_id is not None:
                        mapping = self.db.query(ActivityMapping).filter(
                            ActivityMapping.zammad_type_id == zammad_entry.activity_type_id,
                            ActivityMapping.is_active == True
                        ).first()
                        if mapping:
                            kimai_activity_id = mapping.kimai_activity_id
                            log.debug(f"Found activity mapping: Zammad {zammad_entry.activity_type_id} → Kimai {kimai_activity_id}")
                    
                    # Use default activity if no mapping found
                    if kimai_activity_id is None:
                        # Debug: show config structure
                        log.debug(f"Kimai connector config: {self.kimai_connector.config}")
                        settings = self.kimai_connector.config.get("settings", {})
                        log.debug(f"Kimai connector settings: {settings}")
                        default_activity_id = settings.get("default_activity_id")
                        
                        if default_activity_id:
                            kimai_activity_id = int(default_activity_id)  # Ensure it's an integer
                            log.info(f"Using default Kimai activity {kimai_activity_id} for unmapped Zammad activity {zammad_entry.activity_type_id}")
                        else:
                            log.warning(f"No mapping for activity_type_id {zammad_entry.activity_type_id} and no default_activity_id configured.")
                            log.warning(f"To fix: Go to Connectors page → Edit Kimai connector → Add 'default_activity_id' field with a valid Kimai activity ID (e.g., 1)")
                            conflict_data = ConflictCreate(
                                conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                                zammad_data=zammad_entry.model_dump(),
                                kimai_data=None,
                                notes=f"Unmapped activity type {zammad_entry.activity_type_id}; configure mapping or set default_activity_id in Kimai connector settings"
                            )
                            db_conflict = DBConflict(**conflict_data.model_dump())
                            self.db.add(db_conflict)
                            self.db.commit()
                            self.db.refresh(db_conflict)
                            stats["conflicts"] += 1
                            stats["unmapped"] += 1
                            log.info(f"Logged unmapped conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")
                            continue
                    
                    # Proceed with creation using determined activity ID
                    try:
                            # Step 1: Determine customer name
                            log.debug(f"Determining customer for Zammad entry {zammad_entry.source_id}")
                            customer_name = self._determine_customer_name(zammad_entry)
                            log.info(f"Customer name determined: {customer_name}")
                            
                            # Step 2: Find or create customer
                            log.debug(f"Ensuring customer '{customer_name}' exists in Kimai")
                            customer = await self._ensure_customer(zammad_entry, customer_name)
                            log.info(f"Customer ensured: {customer['name']} (ID: {customer['id']})")
                            
                            # Step 3: Find or create project for this ticket
                            log.debug(f"Ensuring project for ticket {zammad_entry.ticket_id}")
                            project = await self._ensure_project(zammad_entry, customer['id'])
                            log.info(f"Project ensured: {project['name']} (ID: {project['id']})")
                            
                            # Step 4: Create timesheet with proper formatting
                            log.debug(f"Creating timesheet for Zammad entry {zammad_entry.source_id}")
                            timesheet = await self._create_timesheet(zammad_entry, project['id'], kimai_activity_id)
                            log.info(f"Successfully created Kimai timesheet: {timesheet.get('id')}")
                            stats["created"] += 1
                            # Future: Store linkage in our database
                            
                    except ValueError as e:
                            log.error(f"Failed to create Kimai entry for Zammad {zammad_entry.source_id}: {e}")
                            log.debug(f"ValueError details: {str(e)}")
                            # Store as conflict
                            conflict_data = ConflictCreate(
                                conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                                zammad_data=zammad_entry.model_dump(),
                                kimai_data=None,
                                notes=f"Failed to create Kimai entry: {str(e)}"
                            )
                            db_conflict = DBConflict(**conflict_data.model_dump())
                            self.db.add(db_conflict)
                            self.db.commit()
                            self.db.refresh(db_conflict)
                            stats["conflicts"] += 1
                            log.info(f"Logged conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")
                    except Exception as e:
                        log.error(f"Unexpected error creating Kimai entry for Zammad {zammad_entry.source_id}: {e}")
                        log.error(f"Stack trace: {traceback.format_exc()}")
                        conflict_data = ConflictCreate(
                            conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                            zammad_data=zammad_entry.model_dump(),
                            kimai_data=None,
                            notes=f"Unexpected error: {str(e)}"
                        )
                        db_conflict = DBConflict(**conflict_data.model_dump())
                        self.db.add(db_conflict)
                        self.db.commit()
                        self.db.refresh(db_conflict)
                        stats["conflicts"] += 1
                        log.info(f"Logged conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")

                elif reconciled_entry.reconciliation_status == ReconciliationStatus.CONFLICT:
                    log.warning(f"CONFLICT: Zammad {reconciled_entry.zammad_entry.source_id} and Kimai {reconciled_entry.kimai_entry.source_id} differ. Logging conflict...")
                    log.debug(f"Conflict details: Zammad={reconciled_entry.zammad_entry.model_dump()}, Kimai={reconciled_entry.kimai_entry.model_dump()}")
                    conflict_data = ConflictCreate(
                        conflict_type=ReconciliationStatus.CONFLICT,
                        zammad_data=reconciled_entry.zammad_entry.model_dump(),
                        kimai_data=reconciled_entry.kimai_entry.model_dump(),
                        notes="Time entries exist in both systems but have differing details."
                    )
                    db_conflict = DBConflict(**conflict_data.model_dump())
                    self.db.add(db_conflict)
                    self.db.commit()
                    self.db.refresh(db_conflict)
                    stats["conflicts"] += 1
                    log.info(f"Logged conflict (ID: {db_conflict.id})")

                elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_ZAMMAD:
                    log.debug(f"MISSING IN ZAMMAD (Kimai only): Kimai entry {reconciled_entry.kimai_entry.source_id} not found in Zammad. (Ignored for Zammad->Kimai sync)")

            # Final stats
            log.info(f"=== Sync complete: processed={stats['processed']}, created={stats['created']}, conflicts={stats['conflicts']} ===")
            return stats

        except Exception as e:
            log.error(f"Fatal error in sync_time_entries: {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Sync process failed: {str(e)}")

    def _determine_customer_name(self, zammad_entry: TimeEntryNormalized) -> str:
        """
        Determines the customer name from Zammad entry.
        Priority: organization name > user email local part
        """
        log.debug(f"Determining customer name for Zammad entry {zammad_entry.source_id}")
        
        if hasattr(zammad_entry, 'org_name') and zammad_entry.org_name:
            log.debug(f"Using organization name: {zammad_entry.org_name}")
            return zammad_entry.org_name
        
        # Fallback to user email local part
        if hasattr(zammad_entry, 'user_email') and zammad_entry.user_email:
            email_local = zammad_entry.user_email.split('@')[0]
            log.debug(f"Using user email local part: {email_local}")
            return email_local
        elif hasattr(zammad_entry, 'user_emails') and zammad_entry.user_emails and len(zammad_entry.user_emails) > 0:
            email_local = zammad_entry.user_emails[0].split('@')[0]
            log.debug(f"Using first user email local part: {email_local}")
            return email_local
        
        # Ultimate fallback
        fallback_name = f"Zammad User {zammad_entry.ticket_id}"
        log.warning(f"No suitable customer name found, using fallback: {fallback_name}")
        return fallback_name

    async def _ensure_customer(self, zammad_entry: TimeEntryNormalized, customer_name: str) -> Dict[str, Any]:
        """
        Ensures a customer exists in Kimai using deterministic external number lookup.
        Returns the customer object.
        """
        # Determine external number (stable key)
        if hasattr(zammad_entry, 'org_id') and zammad_entry.org_id:
            external_number = f"ZAM-ORG-{zammad_entry.org_id}"
        else:
            # Fallback to user-based number if no organization
            external_number = f"ZAM-USER-{zammad_entry.ticket_id}"
        
        log.debug(f"Looking up customer by external number: {external_number}")
        
        # Try exact match by number first (most deterministic)
        customer = await self.kimai_connector.find_customer_by_number(external_number)
        if customer:
            log.info(f"Customer found by number {external_number}: {customer['name']} (ID: {customer['id']})")
            return customer
        
        # Fallback: try exact name match
        log.debug(f"Customer not found by number, trying exact name match: '{customer_name}'")
        customer = await self.kimai_connector.find_customer_by_name_exact(customer_name)
        if customer:
            log.info(f"Customer found by exact name '{customer_name}': ID {customer['id']}")
            return customer
        
        # Create new customer with external number
        log.info(f"Creating new customer: '{customer_name}' with number {external_number}")
        
        settings = self.kimai_connector.config.get("settings", {})
        
        customer_payload = {
            "name": customer_name,
            "number": external_number,
            "country": settings.get("default_country", "BE"),
            "currency": settings.get("default_currency", "EUR"),
            "timezone": settings.get("default_timezone", "Europe/Brussels"),
            "comment": "Auto-created by Zammad sync",
            "visible": True
        }
        
        # Add email based on customer type
        if hasattr(zammad_entry, 'org_id') and zammad_entry.org_id:
            # Organization customer - fetch contact_email custom field
            org_response = await self.zammad_connector.fetch_organization(zammad_entry.org_id)
            if org_response and org_response.get('contact_email'):
                customer_email = org_response['contact_email']
                customer_payload["email"] = customer_email
                log.debug(f"Using organization contact_email: {customer_email}")
            else:
                # Fallback to dummy email
                customer_payload["email"] = f"org-{zammad_entry.org_id}@zammad.local"
                log.debug(f"Using dummy email for organization customer (no contact_email): {customer_payload['email']}")
        elif hasattr(zammad_entry, 'user_emails') and zammad_entry.user_emails and len(zammad_entry.user_emails) > 1:
            # Individual customer - use ticket customer email (second in list, first is agent)
            customer_payload["email"] = zammad_entry.user_emails[1]
            log.debug(f"Using ticket customer email: {customer_payload['email']}")
        else:
            # Fallback - use dummy email
            customer_payload["email"] = f"customer-{zammad_entry.ticket_id}@zammad.local"
            log.debug(f"Using fallback dummy email: {customer_payload['email']}")
        
        log.debug(f"Customer payload: {customer_payload}")
        
        try:
            new_customer = await self.kimai_connector.create_customer(customer_payload)
            log.info(f"Created customer: {new_customer['name']} (ID: {new_customer['id']}, number: {external_number})")
            return new_customer
        except Exception as e:
            log.error(f"Failed to create customer '{customer_name}': {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai customer '{customer_name}': {str(e)}")

    async def _ensure_project(self, zammad_entry: TimeEntryNormalized, customer_id: int) -> Dict[str, Any]:
        """
        Ensures a project exists in Kimai for the Zammad ticket, creating if necessary.
        Ensures the project allows global activities.
        Returns the project object.
        """
        # Use ticket number as search term
        ticket_number = zammad_entry.ticket_number or str(zammad_entry.ticket_id)
        log.debug(f"Searching for existing project using ticket number: '{ticket_number}' for customer ID {customer_id}")
        
        # Try to find existing project
        project = await self.kimai_connector.find_project(customer_id, ticket_number)
        if project:
            log.info(f"Found existing project: {project['name']} (ID: {project['id']})")
            
            # Check if project allows global activities
            if project.get('globalActivities') is False:
                log.warning(f"Project {project['id']} has globalActivities=false, enabling it now")
                try:
                    project = await self.kimai_connector.patch_project(
                        project['id'], 
                        {"globalActivities": True}
                    )
                    log.info(f"Enabled globalActivities for project {project['id']}")
                except Exception as e:
                    log.error(f"Failed to enable globalActivities for project {project['id']}: {e}")
                    # Continue anyway - the timesheet creation might still work
            
            return project
        
        # Create new project with globalActivities enabled
        project_name = f"Ticket-{ticket_number}"
        log.debug(f"Project name: {project_name}")
        
        # Build Zammad ticket URL for project description
        zammad_base_url = self.zammad_connector.base_url.rstrip('/')
        ticket_url = f"{zammad_base_url}/#ticket/zoom/{zammad_entry.ticket_id}"
        
        # Include globalActivities in creation payload
        project_payload = {
            "name": project_name,
            "customer": int(customer_id),  # Ensure it's an integer
            "comment": ticket_url,  # Add Zammad URL to project description
            "visible": True,
            "globalActivities": True  # Enable global activities from the start
        }
        
        log.info(f"Creating project with payload: {project_payload}")
        
        try:
            new_project = await self.kimai_connector.create_project(project_payload)
            log.info(f"Successfully created project: {new_project['name']} (ID: {new_project['id']}) with globalActivities=true")
            return new_project
        except Exception as e:
            log.error(f"Failed to create project '{project_name}': {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai project '{project_name}': {str(e)}")

    def _to_local_html5(self, iso_timestamp: str, timezone: str = "Europe/Brussels") -> str:
        """
        Convert ISO-8601 timestamp to HTML5 local datetime in specified timezone.
        Returns format: YYYY-MM-DDTHH:MM:SS (no timezone suffix).
        """
        try:
            # Parse ISO timestamp (handles both Z and +00:00 formats)
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            
            # Convert to target timezone
            tz = ZoneInfo(timezone)
            dt_local = dt.astimezone(tz)
            
            # Return as HTML5 local datetime (no timezone)
            return dt_local.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            log.error(f"Failed to convert timestamp '{iso_timestamp}' to local HTML5: {e}")
            raise

    async def _create_timesheet(
        self, 
        zammad_entry: TimeEntryNormalized, 
        project_id: int, 
        activity_id: int
    ) -> Dict[str, Any]:
        """
        Creates a timesheet in Kimai with proper timestamp handling and idempotent upsert.
        Checks for existing timesheet with same marker before creating.
        """
        log.debug(f"Creating timesheet for Zammad entry {zammad_entry.source_id}, project {project_id}, activity {activity_id}")
        
        # Get timezone from connector settings
        settings = self.kimai_connector.config.get("settings", {})
        timezone = settings.get("default_timezone", "Europe/Brussels")
        
        # Use real timestamp from Zammad's created_at
        if zammad_entry.created_at:
            try:
                begin_local = self._to_local_html5(zammad_entry.created_at, timezone)
                log.trace(f"Converted Zammad created_at {zammad_entry.created_at} to local begin: {begin_local}")
            except Exception as e:
                log.warning(f"Failed to parse created_at '{zammad_entry.created_at}', falling back to 09:00: {e}")
                # Fallback to date + 09:00
                entry_dt = datetime.strptime(zammad_entry.entry_date, '%Y-%m-%d')
                begin_local = entry_dt.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # Fallback if no created_at (should not happen with new Zammad connector)
            log.warning(f"No created_at timestamp for Zammad entry {zammad_entry.source_id}, using 09:00 fallback")
            entry_dt = datetime.strptime(zammad_entry.entry_date, '%Y-%m-%d')
            begin_local = entry_dt.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
        
        # Calculate end time
        begin_dt = datetime.fromisoformat(begin_local)
        duration_seconds = zammad_entry.duration_sec
        end_dt = begin_dt + timedelta(seconds=duration_seconds)
        end_local = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        log.trace(f"Timesheet times: begin={begin_local}, end={end_local}, duration={(zammad_entry.duration_sec // 60)} min")
        
        # Build identity marker (canonical, unique identifier)
        ticket_id = zammad_entry.ticket_id
        time_accounting_id = zammad_entry.source_id
        marker = f"ZAM:T{ticket_id}|TA:{time_accounting_id}"
        
        # Build standardized description with marker at the beginning
        ticket_ref = zammad_entry.ticket_number or f"#{ticket_id}"
        customer_full_name = zammad_entry.customer_name or "Unknown Customer"
        org_name = zammad_entry.org_name or "-"
        title_part = zammad_entry.ticket_title or ""
        
        description = f"{marker}\n"
        description += f"Ticket-{ticket_ref}\n"
        description += f"Zammad Ticket ID: {ticket_id}\n"
        description += f"Time Accounting ID: {time_accounting_id}\n"
        description += f"Customer: {customer_full_name} - {org_name}\n"
        if title_part:
            description += f"Title: {title_part}\n"
        
        if len(description) > 500:
            description = description[:497] + "..."
        
        log.debug(f"Built description with marker: {marker}")
        
        # IDEMPOTENT UPSERT: Check for existing timesheet with same marker
        # Search within a reasonable date window (±7 days from entry date)
        entry_date_dt = datetime.strptime(zammad_entry.entry_date, '%Y-%m-%d')
        search_begin = (entry_date_dt - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
        search_end = (entry_date_dt + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59")
        
        log.debug(f"Checking for existing timesheet with marker '{marker}' in range {search_begin} to {search_end}")
        
        try:
            # Fetch timesheets in the date window for this project
            existing_timesheets = await self.kimai_connector.fetch_time_entries(
                search_begin.split('T')[0], 
                search_end.split('T')[0]
            )
            
            # Filter by project and scan for marker in description
            for ts in existing_timesheets:
                ts_description = ts.description or ""
                ts_first_line = ts_description.split('\n')[0] if ts_description else ""
                
                # Check if first line matches our marker exactly
                if ts_first_line == marker:
                    log.info(f"Found existing timesheet with marker '{marker}': Kimai ID {ts.source_id}")
                    
                    # Compare current values with what we would create
                    duration_matches = abs(ts.duration_sec - duration_seconds) < 60  # Within 1 minute
                    activity_matches = (ts.activity_type_id == activity_id)
                    
                    if duration_matches and activity_matches:
                        log.info(f"Existing timesheet is identical, skipping creation (no duplicate)")
                        # Return a pseudo-response to indicate success without creation
                        return {
                            "id": ts.source_id,
                            "status": "exists",
                            "message": "Timesheet already exists with same marker and values"
                        }
                    else:
                        # Values differ - this is a conflict
                        log.warning(
                            f"Existing timesheet with marker '{marker}' has different values: "
                            f"duration {ts.duration_sec}s (expected {duration_seconds}s), "
                            f"activity {ts.activity_type_id} (expected {activity_id})"
                        )
                        # Could update here or flag as conflict - for now, skip and log
                        return {
                            "id": ts.source_id,
                            "status": "conflict",
                            "message": "Timesheet exists but values differ"
                        }
            
            log.debug(f"No existing timesheet found with marker '{marker}', proceeding with creation")
            
        except Exception as e:
            log.warning(f"Error checking for existing timesheet: {e}, proceeding with creation anyway")
        
        # Build tags - only source:zammad as required
        tags = ["source:zammad"]
        
        log.debug(f"Timesheet tags: {tags}")
        
        # Build timesheet payload
        timesheet_payload = {
            "project": project_id,
            "activity": activity_id,
            "begin": begin_local,
            "end": end_local,
            "description": description,
            "tags": ",".join(tags)
        }
        
        log.debug(f"Creating timesheet with payload (marker: {marker})")
        
        try:
            timesheet = await self.kimai_connector.create_timesheet(timesheet_payload)
            log.info(f"Created Kimai timesheet ID {timesheet.get('id')} for Zammad entry {time_accounting_id} (marker: {marker})")
            return timesheet
        except ValueError as ve:
            log.error(f"ValueError creating timesheet: {str(ve)}")
            raise ve
        except Exception as e:
            log.error(f"Unexpected error creating timesheet: {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai timesheet: {str(e)}")

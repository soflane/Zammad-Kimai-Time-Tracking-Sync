from typing import List, Dict, Any
from datetime import datetime, timedelta

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
                log.debug(f"Zammad entry {entry.source_id}: ticket {entry.ticket_number}, {entry.time_minutes} min, activity {entry.activity_type_id}")

            stats["zammad_fetched"] = len(zammad_normalized_entries)
            log.info(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

            # 2. Fetch entries from Kimai (already normalized by connector)
            log.debug("Fetching Kimai entries...")
            kimai_normalized_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
            log.debug(f"Kimai entries fetched: {len(kimai_normalized_entries)}")
            
            # Log each entry for debugging
            for entry in kimai_normalized_entries:
                log.trace(f"Kimai entry {entry.source_id}: {entry.description or 'no desc'}, {entry.time_minutes} min")

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
        Ensures a customer exists in Kimai, creating if necessary.
        Returns the customer object.
        """
        log.debug(f"Searching for existing customer: '{customer_name}' (Zammad entry: {zammad_entry.source_id})")
        
        # Try to find existing customer
        customer = await self.kimai_connector.find_customer(customer_name)
        if customer:
            log.info(f"Found existing customer: {customer['name']} (ID: {customer['id']})")
            return customer
        
        log.info(f"Creating new customer: '{customer_name}' for Zammad entry {zammad_entry.source_id}")
        
        # Create new customer
        settings = self.kimai_connector.config.get("settings", {})
        
        # Determine external ID
        if hasattr(zammad_entry, 'org_id') and zammad_entry.org_id:
            external_id = f"ZAM-ORG-{zammad_entry.org_id}"
            log.debug(f"Using org external ID: {external_id}")
        else:
            external_id = f"ZAM-USER-{zammad_entry.ticket_id}"
            log.debug(f"Using user external ID: {external_id}")
        
        customer_payload = {
            "name": customer_name,
            "number": external_id,
            "country": settings.get("default_country", "BE"),
            "currency": settings.get("default_currency", "EUR"),
            "timezone": settings.get("default_timezone", "Europe/Brussels"),
            "comment": "Auto-created by Zammad sync",
            "visible": True
        }
        
        # Add email if available
        if hasattr(zammad_entry, 'user_email') and zammad_entry.user_email:
            customer_payload["email"] = zammad_entry.user_email
            log.debug(f"Added email to customer payload: {zammad_entry.user_email}")
        elif hasattr(zammad_entry, 'user_emails') and zammad_entry.user_emails and len(zammad_entry.user_emails) > 0:
            customer_payload["email"] = zammad_entry.user_emails[0]
            log.debug(f"Added first user email to customer payload: {zammad_entry.user_emails[0]}")
        
        log.debug(f"Customer payload: {customer_payload}")
        
        try:
            new_customer = await self.kimai_connector.create_customer(customer_payload)
            log.info(f"Successfully created customer: {new_customer['name']} (ID: {new_customer['id']})")
            return new_customer
        except Exception as e:
            log.error(f"Failed to create customer '{customer_name}': {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai customer '{customer_name}': {str(e)}")

    async def _ensure_project(self, zammad_entry: TimeEntryNormalized, customer_id: int) -> Dict[str, Any]:
        """
        Ensures a project exists in Kimai for the Zammad ticket, creating if necessary.
        Returns the project object.
        """
        # Use ticket number as search term
        ticket_number = zammad_entry.ticket_number or str(zammad_entry.ticket_id)
        log.debug(f"Searching for existing project using ticket number: '{ticket_number}' for customer ID {customer_id}")
        
        # Try to find existing project
        project = await self.kimai_connector.find_project(customer_id, ticket_number)
        if project:
            log.info(f"Found existing project: {project['name']} (ID: {project['id']})")
            return project
        
        # Create new project
        project_name = f"#{ticket_number}"
        if hasattr(zammad_entry, 'ticket_title') and zammad_entry.ticket_title:
            project_name += f" – {zammad_entry.ticket_title[:100]}"  # Limit length
            log.debug(f"Project name with title: {project_name}")
        else:
            log.debug(f"Project name without title: {project_name}")
        
        project_payload = {
            "name": project_name,
            "customer": customer_id,
            "number": f"ZAM-TICKET-{zammad_entry.ticket_id}",
            "globalActivities": True,  # Allow global activities for easier mapping
            "visible": True,
            "billable": True
        }
        
        log.debug(f"Project payload: {project_payload}")
        
        try:
            new_project = await self.kimai_connector.create_project(project_payload)
            log.info(f"Successfully created project: {new_project['name']} (ID: {new_project['id']})")
            return new_project
        except Exception as e:
            log.error(f"Failed to create project '{project_name}': {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai project '{project_name}': {str(e)}")

    async def _create_timesheet(
        self, 
        zammad_entry: TimeEntryNormalized, 
        project_id: int, 
        activity_id: int
    ) -> Dict[str, Any]:
        """
        Creates a timesheet in Kimai with proper formatting.
        """
        log.debug(f"Creating timesheet for Zammad entry {zammad_entry.source_id}, project {project_id}, activity {activity_id}")
        
        # Parse entry date and add default time (09:00)
        try:
            entry_dt = datetime.strptime(zammad_entry.entry_date, '%Y-%m-%d')
            begin_dt = entry_dt.replace(hour=9, minute=0, second=0)
            log.debug(f"Parsed entry date {zammad_entry.entry_date} to begin time: {begin_dt}")
        except ValueError as ve:
            log.error(f"Invalid entry date format '{zammad_entry.entry_date}': {ve}")
            raise ValueError(f"Invalid entry date format: {zammad_entry.entry_date}")
        
        # Calculate duration in seconds
        duration_seconds = int(round(zammad_entry.time_minutes * 60))
        log.debug(f"Calculated duration: {zammad_entry.time_minutes} minutes = {duration_seconds} seconds")
        
        # Build description
        ticket_ref = zammad_entry.ticket_number or f"#{zammad_entry.ticket_id}"
        description = f"Zammad {ticket_ref}"
        if hasattr(zammad_entry, 'ticket_title') and zammad_entry.ticket_title:
            description += f": {zammad_entry.ticket_title}"
        if zammad_entry.description:
            description += f"\n\n{zammad_entry.description}"
        
        if len(description) > 500:
            description = description[:497] + "..."
            log.debug("Truncated description to 500 characters")
        
        log.debug(f"Timesheet description: {description}")
        
        # Build tags
        tags = [
            "source:zammad",
            f"ticket:{zammad_entry.ticket_number or zammad_entry.ticket_id}",
            f"zammad_entry:{zammad_entry.source_id}"
        ]
        
        # Add billing tag if we have entry date
        if zammad_entry.entry_date:
            year_month = zammad_entry.entry_date[:7]  # YYYY-MM
            tags.append(f"billed:{year_month}")
            log.debug(f"Added billing tag: billed:{year_month}")
        
        log.debug(f"Timesheet tags: {tags}")
        
        timesheet_payload = {
            "project": project_id,
            "activity": activity_id,
            "begin": begin_dt.strftime('%Y-%m-%dT%H:%M:%S'),  # HTML5 local datetime
            "duration": duration_seconds,
            "description": description,
            "tags": ",".join(tags)  # Kimai expects comma-separated string
        }
        
        log.debug(f"Timesheet payload: {timesheet_payload}")
        
        try:
            timesheet = await self.kimai_connector.create_timesheet(timesheet_payload)
            log.info(f"Successfully created Kimai timesheet ID: {timesheet.get('id')}")
            return timesheet
        except ValueError as ve:
            log.error(f"ValueError creating timesheet: {str(ve)}")
            raise ve
        except Exception as e:
            log.error(f"Unexpected error creating timesheet: {str(e)}")
            log.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"Failed to create Kimai timesheet: {str(e)}")

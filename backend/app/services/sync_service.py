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
        log.info(f"Starting sync from {start_date} to {end_date}")
        
        stats = {
            "processed": 0,
            "created": 0,
            "conflicts": 0
        }

        # 1. Fetch entries from Zammad
        zammad_raw_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
        zammad_normalized_entries: List[TimeEntryNormalized] = []
        for entry in zammad_raw_entries:
            zammad_normalized_entries.append(self.normalizer_service.normalize_zammad_entry(entry)) 

        log.info(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

        # 2. Fetch entries from Kimai
        kimai_raw_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
        kimai_normalized_entries: List[TimeEntryNormalized] = []
        for entry in kimai_raw_entries:
            kimai_normalized_entries.append(self.normalizer_service.normalize_kimai_entry(entry))

        log.info(f"Fetched {len(kimai_normalized_entries)} normalized entries from Kimai.")

        # 3. Reconcile entries
        reconciled_results = await self.reconciliation_service.reconcile_entries(
            zammad_normalized_entries,
            kimai_normalized_entries
        )
        log.info(f"Reconciliation resulted in {len(reconciled_results)} entries.")

        # 4. Process reconciled results
        for reconciled_entry in reconciled_results:
            stats["processed"] += 1
            if reconciled_entry.reconciliation_status == ReconciliationStatus.MATCH:
                log.info(f"MATCH: Zammad {reconciled_entry.zammad_entry.source_id} & Kimai {reconciled_entry.kimai_entry.source_id} are in sync.")
                # Future: Update our DB with association or latest state
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                log.info(f"MISSING IN KIMAI: Zammad entry {reconciled_entry.zammad_entry.source_id} not found in Kimai. Attempting creation...")
                zammad_entry = reconciled_entry.zammad_entry
                
                # Lookup activity mapping
                mapping = self.db.query(ActivityMapping).filter(
                    ActivityMapping.zammad_type_id == zammad_entry.activity_type_id,
                    ActivityMapping.is_active == True
                ).first()
                
                if mapping:
                    try:
                        # Step 1: Determine customer name
                        customer_name = self._determine_customer_name(zammad_entry)
                        log.info(f"Customer name determined: {customer_name}")
                        
                        # Step 2: Find or create customer
                        customer = await self._ensure_customer(zammad_entry, customer_name)
                        log.info(f"Customer ensured: {customer['name']} (ID: {customer['id']})")
                        
                        # Step 3: Find or create project for this ticket
                        project = await self._ensure_project(zammad_entry, customer['id'])
                        log.info(f"Project ensured: {project['name']} (ID: {project['id']})")
                        
                        # Step 4: Create timesheet with proper formatting
                        timesheet = await self._create_timesheet(zammad_entry, project['id'], mapping.kimai_activity_id)
                        log.info(f"Successfully created Kimai timesheet: {timesheet.get('id')}")
                        stats["created"] += 1
                        # Future: Store linkage in our database
                        
                    except ValueError as e:
                        log.error(f"Failed to create Kimai entry for Zammad {zammad_entry.source_id}: {e}")
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
                else:
                    log.warning(f"No active mapping found for Zammad activity_type_id {zammad_entry.activity_type_id}. Logging as conflict.")
                    conflict_data = ConflictCreate(
                        conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                        zammad_data=zammad_entry.model_dump(),
                        kimai_data=None,
                        notes=f"Unmapped activity type {zammad_entry.activity_type_id}; configure mapping first"
                    )
                    db_conflict = DBConflict(**conflict_data.model_dump())
                    self.db.add(db_conflict)
                    self.db.commit()
                    self.db.refresh(db_conflict)
                    stats["conflicts"] += 1
                    log.info(f"Logged unmapped conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")

            elif reconciled_entry.reconciliation_status == ReconciliationStatus.CONFLICT:
                log.warning(f"CONFLICT: Zammad {reconciled_entry.zammad_entry.source_id} and Kimai {reconciled_entry.kimai_entry.source_id} differ. Logging conflict...")
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
                log.info(f"MISSING IN ZAMMAD (Kimai only): Kimai entry {reconciled_entry.kimai_entry.source_id} not found in Zammad. (Ignored for Zammad->Kimai sync)")

        # Log the sync to audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            action="sync",
            entity_type="time_entries",
            user="scheduled",
            details={
                "period": f"{start_date} to {end_date}",
                "stats": stats
            }
        )
        self.db.add(audit_log)
        self.db.commit()
        
        log.info("Sync complete.")
        return stats

    def _determine_customer_name(self, zammad_entry: TimeEntryNormalized) -> str:
        """
        Determines the customer name from Zammad entry.
        Priority: organization name > user email local part
        """
        if hasattr(zammad_entry, 'org_name') and zammad_entry.org_name:
            return zammad_entry.org_name
        
        # Fallback to user email local part
        if hasattr(zammad_entry, 'user_email') and zammad_entry.user_email:
            return zammad_entry.user_email.split('@')[0]
        elif hasattr(zammad_entry, 'user_emails') and zammad_entry.user_emails and len(zammad_entry.user_emails) > 0:
            return zammad_entry.user_emails[0].split('@')[0]
        
        # Ultimate fallback
        return f"Zammad User {zammad_entry.ticket_id}"

    async def _ensure_customer(self, zammad_entry: TimeEntryNormalized, customer_name: str) -> Dict[str, Any]:
        """
        Ensures a customer exists in Kimai, creating if necessary.
        Returns the customer object.
        """
        # Try to find existing customer
        customer = await self.kimai_connector.find_customer(customer_name)
        if customer:
            return customer
        
        # Create new customer
        settings = self.kimai_connector.config.get("settings", {})
        
        # Determine external ID
        if hasattr(zammad_entry, 'org_id') and zammad_entry.org_id:
            external_id = f"ZAM-ORG-{zammad_entry.org_id}"
        else:
            external_id = f"ZAM-USER-{zammad_entry.ticket_id}"
        
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
        elif hasattr(zammad_entry, 'user_emails') and zammad_entry.user_emails and len(zammad_entry.user_emails) > 0:
            customer_payload["email"] = zammad_entry.user_emails[0]
        
        return await self.kimai_connector.create_customer(customer_payload)

    async def _ensure_project(self, zammad_entry: TimeEntryNormalized, customer_id: int) -> Dict[str, Any]:
        """
        Ensures a project exists in Kimai for the Zammad ticket, creating if necessary.
        Returns the project object.
        """
        # Use ticket number as search term
        ticket_number = zammad_entry.ticket_number or str(zammad_entry.ticket_id)
        
        # Try to find existing project
        project = await self.kimai_connector.find_project(customer_id, ticket_number)
        if project:
            return project
        
        # Create new project
        project_name = f"#{ticket_number}"
        if hasattr(zammad_entry, 'ticket_title') and zammad_entry.ticket_title:
            project_name += f" – {zammad_entry.ticket_title[:100]}"  # Limit length
        
        project_payload = {
            "name": project_name,
            "customer": customer_id,
            "number": f"ZAM-TICKET-{zammad_entry.ticket_id}",
            "globalActivities": True,  # Allow global activities for easier mapping
            "visible": True,
            "billable": True
        }
        
        return await self.kimai_connector.create_project(project_payload)

    async def _create_timesheet(
        self, 
        zammad_entry: TimeEntryNormalized, 
        project_id: int, 
        activity_id: int
    ) -> Dict[str, Any]:
        """
        Creates a timesheet in Kimai with proper formatting.
        """
        # Parse entry date and add default time (09:00)
        entry_dt = datetime.strptime(zammad_entry.entry_date, '%Y-%m-%d')
        begin_dt = entry_dt.replace(hour=9, minute=0, second=0)
        
        # Calculate duration in seconds
        duration_seconds = int(round(zammad_entry.time_minutes * 60))
        
        # Build description
        ticket_ref = zammad_entry.ticket_number or f"#{zammad_entry.ticket_id}"
        description = f"Zammad {ticket_ref}"
        if hasattr(zammad_entry, 'ticket_title') and zammad_entry.ticket_title:
            description += f": {zammad_entry.ticket_title}"
        if zammad_entry.description:
            description += f"\n\n{zammad_entry.description}"
        
        # Build tags
        tags = [
            "source:zammad",
            f"ticket:{zammad_entry.ticket_number or zammad_entry.ticket_id}",
            f"zammad_entry:{zammad_entry.source_id}"
        ]
        
        # Add billing tag if we have entry date
        if zammad_entry.entry_date:
            year_month = zammad_entry.entry_date[:7].replace('-', '-')  # YYYY-MM
            tags.append(f"billed:{year_month}")
        
        timesheet_payload = {
            "project": project_id,
            "activity": activity_id,
            "begin": begin_dt.strftime('%Y-%m-%dT%H:%M:%S'),  # HTML5 local datetime
            "duration": duration_seconds,
            "description": description[:500],  # Limit description length
            "tags": ",".join(tags)  # Kimai expects comma-separated string
        }
        
        return await self.kimai_connector.create_timesheet(timesheet_payload)

from typing import List, Dict, Any
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

import logging

from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.connectors.base import TimeEntryNormalized
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService, ReconciledTimeEntry, ReconciliationStatus
from app.models.conflict import Conflict as DBConflict
from app.schemas.conflict import ConflictCreate
from app.models.mapping import ActivityMapping
from app.models.sync_run import SyncRun
from app.models.time_entry import TimeEntry
from app.models.connector import Connector as DBConnector
from app.constants.conflict_reasons import ReasonCode, explain_reason
from sqlalchemy import or_, and_
from app.schemas.connector import KimaiConnectorConfig
from typing import Dict, Any
import traceback

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
        db: Session
    ):
        self.zammad_connector = zammad_connector
        self.kimai_connector = kimai_connector
        self.normalizer_service = normalizer_service
        self.reconciliation_service = reconciliation_service
        self.db = db
        self.kimai_config = self.kimai_connector.config.get('settings', {}) if hasattr(self.kimai_connector, 'config') and 'settings' in self.kimai_connector.config else {}
        
        # Inject Kimai connector into reconciliation service for rounding-aware matching
        if self.reconciliation_service and not self.reconciliation_service.kimai_connector:
            self.reconciliation_service.kimai_connector = self.kimai_connector
            log.debug("Injected Kimai connector into ReconciliationService for rounding-aware matching")

    def _determine_customer_name(self, entry: TimeEntryNormalized) -> str:
        if entry.org_name:
            return entry.org_name
        if entry.customer_name:
            return entry.customer_name
        if entry.user_email:
            return entry.user_email
        return 'Unknown Customer'

    async def _ensure_customer(self, entry: TimeEntryNormalized, customer_name: str) -> Dict[str, Any]:
        if not customer_name or customer_name == 'Unknown Customer':
            customer_name = 'Zammad Default Customer'
        
        # Prefer external ID lookup
        external_id = f"OID-{entry.org_id}" if entry.org_id else None
        customer = None
        if external_id:
            customer = await self.kimai_connector.find_customer_by_number(external_id)
        
        # Fallback to exact name match
        if not customer:
            customer = await self.kimai_connector.find_customer_by_name_exact(customer_name)
        
        # Create if not found
        if not customer:
            payload = {
                "name": customer_name,
                "number": external_id or "",
                "comment": "",
                "company": "",
                "vatId": "",
                "contact": "",
                "address": "",
                "country": self.kimai_config.get('default_country', 'BE'),
                "currency": self.kimai_config.get('default_currency', 'EUR'),
                "phone": "",
                "fax": "",
                "mobile": "",
                "email": "",
                "homepage": "",
                "timezone": self.kimai_config.get('default_timezone', 'Europe/Brussels'),
                "invoiceText": "",
                "visible": True,
                "billable": True
            }
            log.debug(f"Creating customer payload: {payload}")
            try:
                customer = await self.kimai_connector.create_customer(payload)
                log.info(f"Created customer '{customer_name}' (ID: {customer['id']})")
            except Exception as e:
                log.error(f"Failed to create customer '{customer_name}': {e}")
                raise ValueError(f"Customer creation failed: {str(e)}")
        
        log.trace(f"Using customer '{customer['name']}' (ID: {customer['id']}) for entry {entry.source_id}")
        return customer

    async def _ensure_project(self, entry: TimeEntryNormalized, customer_id: int) -> Dict[str, Any]:
        project_name = f"Ticket-{entry.ticket_number}"
        # project_name = f"#{entry.ticket_number} – {entry.ticket_title[:100] if entry.ticket_title else 'Zammad Ticket'}"
        external_id = f"TID-{entry.ticket_id}"
        
        # Prefer external ID lookup
        project = await self.kimai_connector.find_project_by_number(customer_id, external_id)
        
        # Fallback to search
        if not project:
            project = await self.kimai_connector.find_project(customer_id, entry.ticket_number or str(entry.ticket_id))
        
        # Validate customer exists before creating project
        try:
            customer = await self.kimai_connector.get_customer(customer_id)
            log.debug(f"Validated customer {customer_id}: {customer['name']}")
        except ValueError as ve:
            log.error(f"Invalid customer {customer_id}: {ve}")
            raise ValueError(f"Cannot create project: Invalid customer {customer_id} - {ve}")
        
        # Create if not found
        if not project:
            payload = {
                "name": project_name,
                "customer": int(customer_id),
                "number": external_id,
            }
            log.debug(f"Creating project with minimal payload: {payload}")
            try:
                project = await self.kimai_connector.create_project(payload)
                log.info(f"Created project '{project_name}' (ID: {project['id']})")
                
                # Always enable globalActivities and visible after creation
                update_payload = {"globalActivities": True, "visible": True}
                updated_project = await self.kimai_connector.patch_project(project['id'], update_payload)
                log.debug(f"Updated project {project['id']} with globalActivities and visible")
                project = updated_project
                
                # Number set on creation; no additional PATCH needed
            except Exception as e:
                log.error(f"Failed to create/update project '{project_name}': {e}")
                log.error(f"Payload was: {payload}")
                raise ValueError(f"Project creation failed: {str(e)}")
        
        log.trace(f"Using project '{project['name']}' (ID: {project['id']}) for entry {entry.source_id}")
        return project

    async def _create_timesheet(self, entry: TimeEntryNormalized, project_id: int, activity_id: int) -> Dict[str, Any]:
        customer_name = self._determine_customer_name(entry)
        zammad_url = self.zammad_connector.base_url.rstrip('/') + f"/#ticket/zoom/{entry.ticket_id}"
        description = f"""ZAM:T{entry.ticket_id}|TA:{entry.source_id}
Ticket-{entry.ticket_number}
Zammad Ticket ID: {entry.ticket_id}
Time Accounting ID: {entry.source_id}
Customer: {customer_name}
Title: {entry.ticket_title or 'N/A'}
Zammad URL: {zammad_url}
{entry.description}"""
        tags = "source:zammad"
        
        payload = {
            "project": project_id,
            "activity": activity_id,
            "begin": entry.begin_time,
            "end": entry.end_time,
            "description": description,
            "tags": tags
        }
        
        try:
            timesheet = await self.kimai_connector.create_timesheet(payload)
            log.info(f"Created timesheet for Zammad entry {entry.source_id} (Kimai ID: {timesheet['id']})")
            return {'id': timesheet['id'], 'status': 'created'}
        except Exception as e:
            log.error(f"Failed to create timesheet for {entry.source_id}: {e}")
            return {'status': 'error', 'error': str(e)}

    async def sync_time_entries(self, start_date: str, end_date: str, sync_run: SyncRun, trigger_type: str = 'manual') -> dict:
        """
        Performs a full synchronization cycle for time entries within the given date range.
        Returns stats: {'processed': int, 'created': int, 'conflicts': int}
        """
        stats = {
            "processed": 0,
            "created": 0,
            "conflicts": 0,
            "skipped": 0,
            "zammad_fetched": 0,
            "kimai_fetched": 0,
            "reconciled_matches": 0,
            "reconciled_missing_kimai": 0,
            "reconciled_conflicts": 0,
            "unmapped": 0,
            "ignored_unmapped": 0,
            "skipped_duplicates": 0
        }
        try:
            log.info(f"Starting sync: {start_date} to {end_date} (run_id: {sync_run.id})")

            # 1. Fetch entries from Zammad (already normalized by connector)
            zammad_normalized_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
            stats["zammad_fetched"] = len(zammad_normalized_entries)

            # Get Zammad connector ID
            zammad_conn_db = self.db.query(DBConnector).filter(DBConnector.type == "zammad", DBConnector.is_active == True).first()
            if not zammad_conn_db:
                raise ValueError("No active Zammad connector found")
            zammad_connector_id = zammad_conn_db.id

            # Persist Zammad entries as pending TimeEntry records
            source_id_to_te = {}  # source_id -> TimeEntry ID
            for entry in zammad_normalized_entries:
                # Check if already exists (idempotency)
                existing_te = self.db.query(TimeEntry).filter(
                    TimeEntry.source == 'zammad',
                    TimeEntry.source_id == entry.source_id
                ).first()
                if existing_te:
                    log.debug(f"TimeEntry already exists for Zammad {entry.source_id}, skipping insert")
                    source_id_to_te[entry.source_id] = existing_te.id
                    continue

                te = TimeEntry(
                    connector_id=zammad_connector_id,
                    source='zammad',
                    source_id=entry.source_id,
                    ticket_number=entry.ticket_number,
                    ticket_id=entry.ticket_id,
                    description=entry.description,
                    time_minutes=entry.duration_sec / 60.0,
                    activity_type_id=entry.activity_type_id,
                    activity_name=entry.activity_name,
                    user_email=entry.user_email,
                    entry_date=date.fromisoformat(entry.entry_date),
                    sync_status='pending',
                    created_at=datetime.now(ZoneInfo('Europe/Brussels')),
                    updated_at=datetime.now(ZoneInfo('Europe/Brussels'))
                )
                self.db.add(te)
                self.db.flush()  # Flush to get ID without commit
                source_id_to_te[entry.source_id] = te.id
                log.debug(f"Created pending TimeEntry ID {te.id} for Zammad {entry.source_id}")

            self.db.commit()  # Commit pending inserts

            # 2. Fetch existing entries from Kimai
            kimai_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
            stats["kimai_fetched"] = len(kimai_entries)

            # Update fetched count
            sync_run.entries_fetched = len(zammad_normalized_entries) + len(kimai_entries)
            self.db.commit()

            # 3. Reconcile entries
            reconciled = await self.reconciliation_service.reconcile_entries(
                zammad_entries=zammad_normalized_entries,
                kimai_entries=kimai_entries
            )

            # 4. Process reconciled entries
            for rec in reconciled:
                stats["processed"] += 1
                z_entry = rec.zammad_entry if hasattr(rec, 'zammad_entry') else None
                if not z_entry:
                    # Skip non-Zammad focused (e.g., missing in Zammad)
                    stats["skipped"] += 1
                    continue

                te_id = source_id_to_te.get(z_entry.source_id)
                if not te_id:
                    log.warning(f"No TimeEntry found for Zammad {z_entry.source_id}, skipping")
                    stats["skipped"] += 1
                    continue

                te = self.db.query(TimeEntry).get(te_id)

                if rec.reconciliation_status == ReconciliationStatus.MATCH:
                    stats["reconciled_matches"] += 1
                    # Ensure synced status
                    if te.sync_status != 'synced':
                        te.sync_status = 'synced'
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()
                        log.debug(f"Updated TimeEntry {te_id} to 'synced' for match")
                elif rec.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                    stats["reconciled_missing_kimai"] += 1
                    # Create in Kimai
                    customer_name = self._determine_customer_name(z_entry)
                    customer = await self._ensure_customer(z_entry, customer_name)
                    project = await self._ensure_project(z_entry, customer['id'])
                    # Check for activity mapping
                    mapping = self.db.query(ActivityMapping).filter(
                        ActivityMapping.zammad_type_id == z_entry.activity_type_id
                    ).first()
                    if not mapping:
                        ignore_unmapped = self.kimai_config.get('ignore_unmapped_activities', False)
                        if ignore_unmapped:
                            log.warning(f"Ignoring unmapped activity for Zammad entry {z_entry.source_id} (type_id: {z_entry.activity_type_id})")
                            te.sync_status = 'error'
                            te.sync_error = 'Unmapped activity (ignored)'
                            te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                            self.db.commit()
                            stats["ignored_unmapped"] += 1
                            continue  # Skip creation without conflict
                        
                    # Create unmapped conflict
                    context = {
                        'activity_name': z_entry.activity_name or 'Unknown',
                        'zammad_type_id': z_entry.activity_type_id,
                    }
                    detail = explain_reason(ReasonCode.UNMAPPED_ACTIVITY, context)
                    z_minutes = z_entry.duration_sec / 60.0
                    customer_name = self._determine_customer_name(z_entry)
                    project_name = f"Ticket {z_entry.ticket_number or z_entry.ticket_id}"
                    
                    # Deduplication check
                    existing = self.db.query(DBConflict).filter(
                        or_(
                            DBConflict.ticket_number == z_entry.ticket_number,
                            DBConflict.activity_name == z_entry.activity_name
                        ),
                        DBConflict.zammad_created_at == z_entry.created_at,
                        DBConflict.zammad_time_minutes == z_minutes,
                        DBConflict.resolution_status == 'pending'
                    ).first()
                    
                    if existing:
                        log.info(f"Duplicate unmapped conflict skipped for ticket {z_entry.ticket_number}, activity {z_entry.activity_name}")
                        te.sync_status = 'conflict'
                        te.sync_error = detail
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()
                        stats["skipped_duplicates"] += 1
                        continue
                    
                    conflict = DBConflict(
                        conflict_type='conflict',
                        reason_code=ReasonCode.UNMAPPED_ACTIVITY.value,
                        reason_detail=detail,
                        customer_name=customer_name,
                        project_name=project_name,
                        activity_name=z_entry.activity_name,
                        ticket_number=z_entry.ticket_number,
                        zammad_created_at=z_entry.created_at,
                        zammad_entry_date=z_entry.entry_date,
                        zammad_time_minutes=z_minutes,
                        zammad_data=z_entry.model_dump(),  # Store complete Zammad entry data
                        time_entry_id=te_id,
                        resolution_status='pending'
                    )
                    self.db.add(conflict)
                    log.info(f"Created conflict (unmapped_activity) for ticket {z_entry.ticket_number}")
                    self.db.commit()
                    te.sync_status = 'conflict'
                    te.sync_error = detail
                    te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                    self.db.commit()
                    stats["unmapped"] += 1
                    stats["conflicts"] += 1
                    continue  # Skip creation

                    activity_id = mapping.kimai_activity_id
                    timesheet = await self._create_timesheet(z_entry, project['id'], activity_id)
                    if timesheet['status'] == 'created':
                        # Update TimeEntry to synced
                        te.kimai_id = timesheet['id']
                        te.synced_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        te.sync_status = 'synced'
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()
                        stats["created"] += 1
                        log.info(f"Updated TimeEntry {te_id} to 'synced' with Kimai ID {timesheet['id']}")
                    else:
                        # Create conflict for creation error
                        context = {'error_detail': timesheet.get('error', 'Unknown error')}
                        detail = explain_reason(ReasonCode.CREATION_ERROR, context)
                        z_minutes = z_entry.duration_sec / 60.0
                        customer_name = self._determine_customer_name(z_entry)
                        project_name = f"Ticket {z_entry.ticket_number or z_entry.ticket_id}"
                        
                        # Deduplication check
                        existing = self.db.query(DBConflict).filter(
                            DBConflict.ticket_number == z_entry.ticket_number,
                            DBConflict.zammad_created_at == z_entry.created_at,
                            DBConflict.zammad_time_minutes == z_minutes,
                            DBConflict.resolution_status == 'pending'
                        ).first()
                        
                        if existing:
                            log.info(f"Duplicate creation error conflict skipped for ticket {z_entry.ticket_number}")
                            te.sync_status = 'error'
                            te.sync_error = detail
                            te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                            self.db.commit()
                            stats["skipped_duplicates"] += 1
                        else:
                            conflict = DBConflict(
                                conflict_type='missing',
                                reason_code=ReasonCode.CREATION_ERROR.value,
                                reason_detail=detail,
                                customer_name=customer_name,
                                project_name=project_name,
                                activity_name=z_entry.activity_name,
                                ticket_number=z_entry.ticket_number,
                                zammad_created_at=z_entry.created_at,
                                zammad_entry_date=z_entry.entry_date,
                                zammad_time_minutes=z_minutes,
                                zammad_data=z_entry.model_dump(),  # Store complete Zammad entry data
                                time_entry_id=te_id,
                                resolution_status='pending'
                            )
                            self.db.add(conflict)
                            log.info(f"Created missing conflict (creation error) for ticket {z_entry.ticket_number}")
                            self.db.commit()
                            te.sync_status = 'error'
                            te.sync_error = detail
                            te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                            self.db.commit()
                            stats["conflicts"] += 1
                elif rec.reconciliation_status == ReconciliationStatus.CONFLICT:
                    stats["reconciled_conflicts"] += 1
                    # Create conflict record
                    # Determine specific reason
                    k_entry = rec.kimai_entry
                    z_minutes = z_entry.duration_sec / 60.0
                    k_minutes = k_entry.duration_sec / 60.0
                    if abs(z_minutes - k_minutes) > 0.1:  # Tolerance for float
                        reason_code = ReasonCode.TIME_MISMATCH
                        context = {
                            'ticket_number': z_entry.ticket_number,
                            'zammad_minutes': round(z_minutes, 1),
                            'kimai_minutes': round(k_minutes, 1),
                        }
                    else:
                        reason_code = ReasonCode.DUPLICATE
                        context = {
                            'ticket_number': z_entry.ticket_number,
                            'entry_date': str(z_entry.entry_date),
                        }
                    detail = explain_reason(reason_code, context)
                    k_id = int(k_entry.source_id) if k_entry.source_id else None
                    customer_name = self._determine_customer_name(z_entry)
                    project_name = f"Ticket {z_entry.ticket_number or z_entry.ticket_id}"
                    
                    # Deduplication check
                    existing = self.db.query(DBConflict).filter(
                        DBConflict.ticket_number == z_entry.ticket_number,
                        DBConflict.zammad_created_at == z_entry.created_at,
                        DBConflict.zammad_time_minutes == z_minutes,
                        DBConflict.resolution_status == 'pending'
                    ).first()
                    
                    if existing:
                        log.info(f"Duplicate conflict skipped for ticket {z_entry.ticket_number}")
                        te.sync_status = 'conflict'
                        te.sync_error = detail
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()
                        stats["skipped_duplicates"] += 1
                    else:
                        conflict = DBConflict(
                            conflict_type='conflict',
                            reason_code=reason_code.value,
                            reason_detail=detail,
                            customer_name=customer_name,
                            project_name=project_name,
                            activity_name=z_entry.activity_name,
                            ticket_number=z_entry.ticket_number,
                            zammad_created_at=z_entry.created_at,
                            zammad_entry_date=z_entry.entry_date,
                            zammad_time_minutes=z_minutes,
                            zammad_data=z_entry.model_dump(),  # Store complete Zammad entry data
                            kimai_begin=getattr(k_entry, 'begin', None),
                            kimai_end=getattr(k_entry, 'end', None),
                            kimai_duration_minutes=k_minutes,
                            kimai_data=k_entry.model_dump() if k_entry else None,  # Store complete Kimai entry data
                            kimai_id=k_id,
                            time_entry_id=te_id,
                            resolution_status='pending'
                        )
                        self.db.add(conflict)
                        log.info(f"Created conflict ({reason_code.name}) for ticket {z_entry.ticket_number}")
                        self.db.commit()
                        te.sync_status = 'conflict'
                        te.sync_error = detail
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()
                        stats["conflicts"] += 1
                else:
                    stats["skipped"] += 1
                    if te:
                        te.sync_status = 'skipped'
                        te.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
                        self.db.commit()

            # Update SyncRun on success
            sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
            sync_run.status = 'completed'
            sync_run.entries_synced = stats["created"]
            sync_run.entries_already_synced = stats["reconciled_matches"]
            sync_run.entries_skipped = stats["skipped"] + stats.get("ignored_unmapped", 0)
            sync_run.entries_failed = stats.get("unmapped", 0)
            sync_run.conflicts_detected = stats["conflicts"]
            self.db.commit()

            log.info(f"Sync completed: {stats['created']} created, {stats['conflicts']} conflicts, {stats['skipped']} skipped")

            return stats

        except Exception as e:
            # Determine error type for better user feedback
            error_type = "Unknown error"
            if "getaddrinfo failed" in str(e) or "Name or service not known" in str(e):
                error_type = "Connection error: Invalid URL or network issue"
            elif "401" in str(e) or "Unauthorized" in str(e):
                error_type = "Authentication error: Invalid API token"
            elif "403" in str(e) or "Forbidden" in str(e):
                error_type = "Permission error: Insufficient API permissions"
            elif "timeout" in str(e).lower():
                error_type = "Timeout error: Server not responding"
            else:
                error_type = f"Sync error: {str(e)}"
            
            log.error(f"Sync failed - {error_type}")
            log.debug(traceback.format_exc())
            
            if "error" not in stats:
                stats["error"] = error_type
            
            # Update SyncRun on failure
            sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
            sync_run.status = 'failed'
            sync_run.error_message = error_type
            sync_run.entries_synced = stats["created"]
            sync_run.entries_already_synced = stats["reconciled_matches"]
            sync_run.entries_skipped = stats["skipped"] + stats.get("ignored_unmapped", 0)
            sync_run.entries_failed = stats.get("unmapped", 0) + 1
            sync_run.conflicts_detected = stats["conflicts"]
            self.db.commit()

            raise ValueError(error_type)  # Raise with user-friendly message

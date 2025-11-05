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
from app.constants.conflict_reasons import ReasonCode, explain_reason
from sqlalchemy import or_
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
        
        log.debug(f"Using customer '{customer['name']}' (ID: {customer['id']}) for entry {entry.source_id}")
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
        
        log.debug(f"Using project '{project['name']}' (ID: {project['id']}) for entry {entry.source_id}")
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

    async def sync_time_entries(self, start_date: str, end_date: str) -> dict:
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
            log.debug(f"SyncService.sync_time_entries called with period {start_date} to {end_date}")
            log.info(f"=== Starting sync from {start_date} to {end_date} ===")

            # 1. Fetch entries from Zammad (already normalized by connector)
            log.debug("Fetching Zammad entries...")
            zammad_normalized_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
            log.debug(f"Zammad entries fetched: {len(zammad_normalized_entries)}")
            stats["zammad_fetched"] = len(zammad_normalized_entries)

            # 2. Fetch existing entries from Kimai
            log.debug("Fetching Kimai entries...")
            kimai_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
            log.debug(f"Kimai entries fetched: {len(kimai_entries)}")
            stats["kimai_fetched"] = len(kimai_entries)

            # 3. Reconcile entries
            log.debug("Reconciling entries...")
            reconciled = await self.reconciliation_service.reconcile_entries(
                zammad_entries=zammad_normalized_entries,
                kimai_entries=kimai_entries
            )

            # 4. Process reconciled entries
            for rec in reconciled:
                stats["processed"] += 1
                if rec.reconciliation_status == ReconciliationStatus.MATCH:
                    stats["reconciled_matches"] += 1
                    # No action needed, already synced
                elif rec.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                    stats["reconciled_missing_kimai"] += 1
                    # Create in Kimai
                    z_entry = rec.zammad_entry
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
                            stats["ignored_unmapped"] += 1
                            continue  # Skip creation without conflict
                        
                        # Create unmapped conflict
                        context = {
                            'activity_name': z_entry.activity_name or 'Unknown',
                            'zammad_type_id': z_entry.activity_type_id,
                        }
                        detail = explain_reason(ReasonCode.UNMAPPED_ACTIVITY, context)
                        z_minutes = z_entry.duration_sec / 60.0 if hasattr(z_entry, 'duration_sec') else z_entry.time_minutes
                        customer_name = self._determine_customer_name(z_entry)
                        project_name = f"Ticket {z_entry.ticket_number or z_entry.ticket_id}"
                        
                        # Deduplication check
                        existing = self.db.query(DBConflict).filter(
                            or_(
                                DBConflict.ticket_number == z_entry.ticket_number,
                                and_(DBConflict.activity_name == z_entry.activity_name, DBConflict.zammad_type_id == z_entry.activity_type_id)
                            ),
                            DBConflict.zammad_created_at == z_entry.created_at,
                            DBConflict.zammad_time_minutes == z_minutes,
                            DBConflict.resolution_status == 'pending'
                        ).first()
                        
                        if existing:
                            log.info(f"Duplicate unmapped conflict skipped for ticket {z_entry.ticket_number}, activity {z_entry.activity_name}")
                            stats["skipped_duplicates"] += 1
                            continue
                        
                        conflict = DBConflict(
                            conflict_type='unmapped_activity',
                            reason_code=ReasonCode.UNMAPPED_ACTIVITY.value,
                            reason_detail=detail,
                            customer_name=customer_name,
                            project_name=project_name,
                            activity_name=z_entry.activity_name,
                            ticket_number=z_entry.ticket_number,
                            zammad_created_at=z_entry.created_at,
                            zammad_entry_date=z_entry.entry_date,
                            zammad_time_minutes=z_minutes,
                            resolution_status='pending'
                        )
                        self.db.add(conflict)
                        self.db.commit()
                        stats["unmapped"] += 1
                        stats["conflicts"] += 1
                        continue  # Skip creation

                    activity_id = mapping.kimai_activity_id
                    timesheet = await self._create_timesheet(z_entry, project['id'], activity_id)
                    if timesheet['status'] == 'created':
                        stats["created"] += 1
                    else:
                        # Create conflict for creation error
                        context = {'error_detail': timesheet.get('error', 'Unknown error')}
                        detail = explain_reason(ReasonCode.CREATION_ERROR, context)
                        z_minutes = z_entry.duration_sec / 60.0 if hasattr(z_entry, 'duration_sec') else (z_entry.time_minutes or 0)
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
                            stats["skipped_duplicates"] += 1
                        else:
                            conflict = DBConflict(
                                conflict_type='create_failed',
                                reason_code=ReasonCode.CREATION_ERROR.value,
                                reason_detail=detail,
                                customer_name=customer_name,
                                project_name=project_name,
                                activity_name=z_entry.activity_name,
                                ticket_number=z_entry.ticket_number,
                                zammad_created_at=z_entry.created_at,
                                zammad_entry_date=z_entry.entry_date,
                                zammad_time_minutes=z_minutes,
                                resolution_status='pending'
                            )
                            self.db.add(conflict)
                            self.db.commit()
                            stats["conflicts"] += 1
                elif rec.reconciliation_status == ReconciliationStatus.CONFLICT:
                    stats["reconciled_conflicts"] += 1
                    # Create conflict record
                    # Determine specific reason
                    z_entry = rec.zammad_entry
                    k_entry = rec.kimai_entry
                    z_minutes = z_entry.duration_sec / 60.0 if hasattr(z_entry, 'duration_sec') else (z_entry.time_minutes or 0)
                    k_minutes = k_entry.duration_sec / 60.0 if hasattr(k_entry, 'duration_sec') else (k_entry.time_minutes or 0)
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
                    k_id = int(k_entry.id) if k_entry.id else (int(k_entry.source_id) if k_entry.source_id and k_entry.source_id.isdigit() else None)
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
                        stats["skipped_duplicates"] += 1
                    else:
                        conflict = DBConflict(
                            conflict_type='duplicate',
                            reason_code=reason_code.value,
                            reason_detail=detail,
                            customer_name=customer_name,
                            project_name=project_name,
                            activity_name=z_entry.activity_name,
                            ticket_number=z_entry.ticket_number,
                            zammad_created_at=z_entry.created_at,
                            zammad_entry_date=z_entry.entry_date,
                            zammad_time_minutes=z_minutes,
                            kimai_begin=getattr(k_entry, 'begin', None),
                            kimai_end=getattr(k_entry, 'end', None),
                            kimai_duration_minutes=k_minutes,
                            kimai_id=k_id,
                            resolution_status='pending'
                        )
                        self.db.add(conflict)
                        self.db.commit()
                        stats["conflicts"] += 1
                else:
                    stats["skipped"] += 1

            self.db.commit()
            log.info(f"=== Sync completed ===")
            log.info(f"Stats: {stats}")

        except Exception as e:
            log.error(f"Sync failed: {str(e)}")
            log.error(traceback.format_exc())
            if "error" not in stats:
                stats["error"] = str(e)
            self.db.rollback()

        return stats

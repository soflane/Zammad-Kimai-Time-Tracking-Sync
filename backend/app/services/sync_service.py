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

    def _determine_customer_name(self, entry: TimeEntryNormalized) -> str:
        if entry.org_name:
            return entry.org_name
        if entry.user_email:
            return entry.user_email
        return 'Unknown Customer'

    async def _ensure_customer(self, entry: TimeEntryNormalized, customer_name: str) -> Dict[str, Any]:
        # Placeholder to avoid syntax error, implement later
        log.warning("Ensure customer placeholder - not implemented")
        return {'id': 1, 'name': customer_name}

    async def _ensure_project(self, entry: TimeEntryNormalized, customer_id: int) -> Dict[str, Any]:
        # Placeholder
        log.warning("Ensure project placeholder - not implemented")
        return {'id': 1, 'name': f'Ticket-{entry.ticket_number or entry.ticket_id}'}

    async def _create_timesheet(self, entry: TimeEntryNormalized, project_id: int, activity_id: int) -> Dict[str, Any]:
        # Placeholder
        log.warning("Create timesheet placeholder - not implemented")
        return {'id': 1, 'status': 'created'}

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
            "unmapped": 0
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
                        # Create unmapped conflict
                        context = {
                            'activity_name': z_entry.activity_name or 'Unknown',
                            'zammad_type_id': z_entry.activity_type_id,
                        }
                        detail = explain_reason(ReasonCode.UNMAPPED_ACTIVITY, context)
                        conflict = DBConflict(
                            conflict_type='unmapped_activity',
                            reason_code=ReasonCode.UNMAPPED_ACTIVITY.value,
                            reason_detail=detail,
                            customer_name=z_entry.org_name,
                            project_name=f"Ticket {z_entry.ticket_number or z_entry.ticket_id}",
                            activity_name=z_entry.activity_name,
                            ticket_number=z_entry.ticket_number,
                            zammad_created_at=z_entry.created_at,
                            zammad_entry_date=z_entry.entry_date,
                            zammad_time_minutes=z_entry.duration_sec / 60.0 if hasattr(z_entry, 'duration_sec') else z_entry.time_minutes,
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
                        conflict = DBConflict(
                            conflict_type='create_failed',
                            reason_code=ReasonCode.CREATION_ERROR.value,
                            reason_detail=detail,
                            customer_name=z_entry.org_name,
                            project_name=f"Ticket {z_entry.ticket_number or z_entry.ticket_id}",
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
                    conflict = DBConflict(
                        conflict_type='duplicate',
                        reason_code=reason_code.value,
                        reason_detail=detail,
                        customer_name=z_entry.org_name,
                        project_name=f"Ticket {z_entry.ticket_number or z_entry.ticket_id}",
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

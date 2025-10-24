from typing import List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session # Required for database interaction

from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.connectors.base import TimeEntryNormalized
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService, ReconciledTimeEntry, ReconciliationStatus
from app.models.conflict import Conflict as DBConflict # Import DB Conflict model
from app.schemas.conflict import ConflictCreate # Import Pydantic schema for creating conflicts
from app.models.mapping import ActivityMapping


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
        print(f"Starting sync from {start_date} to {end_date}")
        
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

        print(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

        # 2. Fetch entries from Kimai
        kimai_raw_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
        kimai_normalized_entries: List[TimeEntryNormalized] = []
        for entry in kimai_raw_entries:
            kimai_normalized_entries.append(self.normalizer_service.normalize_kimai_entry(entry))

        print(f"Fetched {len(kimai_normalized_entries)} normalized entries from Kimai.")

        # 3. Reconcile entries
        reconciled_results = await self.reconciliation_service.reconcile_entries(
            zammad_normalized_entries,
            kimai_normalized_entries
        )
        print(f"Reconciliation resulted in {len(reconciled_results)} entries.")

        # 4. Process reconciled results
        for reconciled_entry in reconciled_results:
            stats["processed"] += 1
            if reconciled_entry.reconciliation_status == ReconciliationStatus.MATCH:
                print(f"MATCH: Zammad {reconciled_entry.zammad_entry.source_id} & Kimai {reconciled_entry.kimai_entry.source_id} are in sync.")
                # Future: Update our DB with association or latest state
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                print(f"MISSING IN KIMAI: Zammad entry {reconciled_entry.zammad_entry.source_id} not found in Kimai. Attempting creation...")
                zammad_entry = reconciled_entry.zammad_entry
                
                # Lookup activity mapping
                mapping = self.db.query(ActivityMapping).filter(
                    ActivityMapping.zammad_type_id == zammad_entry.activity_type_id,
                    ActivityMapping.is_active == True
                ).first()
                
                if mapping:
                    # Create a copy with mapped Kimai activity
                    mapped_entry = zammad_entry.model_copy(update={
                        "activity_type_id": mapping.kimai_activity_id,
                        "activity_name": mapping.kimai_activity_name
                    })
                    try:
                        created_kimai_entry = await self.kimai_connector.create_time_entry(mapped_entry)
                        print(f"Successfully created Kimai entry: {created_kimai_entry.source_id}")
                        stats["created"] += 1
                        # Future: Store linkage in our database
                    except Exception as e:
                        print(f"Failed to create Kimai entry for Zammad {zammad_entry.source_id}: {e}")
                        # Store as conflict
                        conflict_data = ConflictCreate(
                            conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                            zammad_data=zammad_entry.model_dump(),
                            kimai_data=None, # No corresponding Kimai entry
                            notes=f"Failed to create Kimai entry: {e}"
                        )
                        db_conflict = DBConflict(**conflict_data.model_dump())
                        self.db.add(db_conflict)
                        self.db.commit()
                        self.db.refresh(db_conflict)
                        stats["conflicts"] += 1
                        print(f"Logged conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")
                else:
                    print(f"No active mapping found for Zammad activity_type_id {zammad_entry.activity_type_id}. Logging as conflict.")
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
                    print(f"Logged unmapped conflict for Zammad {zammad_entry.source_id} (ID: {db_conflict.id})")

            elif reconciled_entry.reconciliation_status == ReconciliationStatus.CONFLICT:
                print(f"CONFLICT: Zammad {reconciled_entry.zammad_entry.source_id} and Kimai {reconciled_entry.kimai_entry.source_id} differ. Logging conflict...")
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
                print(f"Logged conflict (ID: {db_conflict.id})")

            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_ZAMMAD:
                print(f"MISSING IN ZAMMAD (Kimai only): Kimai entry {reconciled_entry.kimai_entry.source_id} not found in Zammad. (Ignored for Zammad->Kimai sync)")

        # Log the sync to audit
        from app.models.audit_log import AuditLog
        audit_log = AuditLog(
            action="sync",
            entity_type="time_entries",
            user=current_user.username if 'current_user' in locals() else "scheduled",
            details={
                "period": f"{start_date} to {end_date}",
                "stats": stats
            }
        )
        self.db.add(audit_log)
        self.db.commit()
        
        print("Sync complete.")
        return stats

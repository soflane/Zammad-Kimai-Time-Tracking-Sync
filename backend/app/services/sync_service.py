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

    async def sync_time_entries(self, start_date: str, end_date: str):
        """
        Performs a full synchronization cycle for time entries within the given date range.
        - Fetches Zammad entries
        - Fetches Kimai entries
        - Normalizes both
        - Reconciles them
        - Creates / updates missing entries in Kimai
        - Flags conflicts for manual review (persists to DB)
        """
        print(f"Starting sync from {start_date} to {end_date}")

        # 1. Fetch entries from Zammad
        zammad_raw_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
        zammad_normalized_entries: List[TimeEntryNormalized] = []
        for entry in zammad_raw_entries:
            zammad_normalized_entries.append(entry) 

        print(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

        # 2. Fetch entries from Kimai
        kimai_raw_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
        kimai_normalized_entries: List[TimeEntryNormalized] = []
        for entry in kimai_raw_entries:
            kimai_normalized_entries.append(entry)

        print(f"Fetched {len(kimai_normalized_entries)} normalized entries from Kimai.")

        # 3. Reconcile entries
        reconciled_results = await self.reconciliation_service.reconcile_entries(
            zammad_normalized_entries,
            kimai_normalized_entries
        )
        print(f"Reconciliation resulted in {len(reconciled_results)} entries.")

        # 4. Process reconciled results
        for reconciled_entry in reconciled_results:
            if reconciled_entry.reconciliation_status == ReconciliationStatus.MATCH:
                print(f"MATCH: Zammad {reconciled_entry.zammad_entry.source_id} & Kimai {reconciled_entry.kimai_entry.source_id} are in sync.")
                # Future: Update our DB with association or latest state
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                print(f"MISSING IN KIMAI: Zammad entry {reconciled_entry.zammad_entry.source_id} not found in Kimai. Attempting creation...")
                try:
                    created_kimai_entry = await self.kimai_connector.create_time_entry(reconciled_entry.zammad_entry)
                    print(f"Successfully created Kimai entry: {created_kimai_entry.source_id}")
                    # Future: Store linkage in our database
                except Exception as e:
                    print(f"Failed to create Kimai entry for Zammad {reconciled_entry.zammad_entry.source_id}: {e}")
                    # Store as conflict
                    conflict_data = ConflictCreate(
                        conflict_type=ReconciliationStatus.MISSING_IN_KIMAI,
                        zammad_data=reconciled_entry.zammad_entry.model_dump(),
                        kimai_data=None, # No corresponding Kimai entry
                        notes=f"Failed to create Kimai entry: {e}"
                    )
                    db_conflict = DBConflict(**conflict_data.model_dump())
                    self.db.add(db_conflict)
                    self.db.commit()
                    self.db.refresh(db_conflict)
                    print(f"Logged conflict for Zammad {reconciled_entry.zammad_entry.source_id} (ID: {db_conflict.id})")

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
                print(f"Logged conflict (ID: {db_conflict.id})")

            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_ZAMMAD:
                print(f"MISSING IN ZAMMAD (Kimai only): Kimai entry {reconciled_entry.kimai_entry.source_id} not found in Zammad. (Ignored for Zammad->Kimai sync)")
        
        print("Sync complete.")

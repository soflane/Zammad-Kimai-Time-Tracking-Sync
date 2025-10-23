from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.connectors.base import TimeEntryNormalized
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService, ReconciledTimeEntry, ReconciliationStatus
# Assuming database session can be passed to service or managed via dependency injection
# from sqlalchemy.orm import Session
# from app.models.time_entry import TimeEntry # Assuming we'll store time entries in our DB
# from app.models.conflict import Conflict # Assuming we'll store conflicts in our DB

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
        # db: Session # Inject database session if needed for persistent storage
    ):
        self.zammad_connector = zammad_connector
        self.kimai_connector = kimai_connector
        self.normalizer_service = normalizer_service
        self.reconciliation_service = reconciliation_service
        # self.db = db

    async def sync_time_entries(self, start_date: str, end_date: str):
        """
        Performs a full synchronization cycle for time entries within the given date range.
        - Fetches Zammad entries
        - Fetches Kimai entries
        - Normalizes both
        - Reconciles them
        - Creates / updates missing entries in Kimai
        - Flags conflicts for manual review (in V1, prints to console)
        """
        print(f"Starting sync from {start_date} to {end_date}")

        # 1. Fetch entries from Zammad
        zammad_raw_entries = await self.zammad_connector.fetch_time_entries(start_date, end_date)
        zammad_normalized_entries: List[TimeEntryNormalized] = []
        for entry in zammad_raw_entries:
            # In a real scenario, zammad_raw_entries would be raw dicts
            # For now, it's already normalized due to mock in zammad_connector
            zammad_normalized_entries.append(entry) 
            # Or if raw: self.normalizer_service.normalize_zammad_entry(entry)

        print(f"Fetched {len(zammad_normalized_entries)} normalized entries from Zammad.")

        # 2. Fetch entries from Kimai
        kimai_raw_entries = await self.kimai_connector.fetch_time_entries(start_date, end_date)
        kimai_normalized_entries: List[TimeEntryNormalized] = []
        for entry in kimai_raw_entries:
            # Similar to Zammad, kimai_raw_entries are already normalized due to mock
            kimai_normalized_entries.append(entry)
            # Or if raw: self.normalizer_service.normalize_kimai_entry(entry)

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
                # No action needed, but could update our DB with association or latest state
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_KIMAI:
                print(f"MISSING IN KIMAI: Zammad entry {reconciled_entry.zammad_entry.source_id} not found in Kimai. Creating...")
                try:
                    # Attempt to create the entry in Kimai
                    created_kimai_entry = await self.kimai_connector.create_time_entry(reconciled_entry.zammad_entry)
                    print(f"Successfully created Kimai entry: {created_kimai_entry.source_id}")
                    # Here, you would typically store the linkage (Zammad ID -> Kimai ID) in your database
                except Exception as e:
                    print(f"Failed to create Kimai entry for Zammad {reconciled_entry.zammad_entry.source_id}: {e}")
                    # Log as conflict or error for manual review
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.CONFLICT:
                print(f"CONFLICT: Zammad {reconciled_entry.zammad_entry.source_id} and Kimai {reconciled_entry.kimai_entry.source_id} differ.")
                # In V1, we just print this. In future, store in `Conflict` model for UI resolution.
            elif reconciled_entry.reconciliation_status == ReconciliationStatus.MISSING_IN_ZAMMAD:
                print(f"MISSING IN ZAMMAD (Kimai only): Kimai entry {reconciled_entry.kimai_entry.source_id} not found in Zammad. (Ignored for Zammad->Kimai sync)")
                # This might indicate entries created directly in Kimai, outside Zammad.
                # Depending on business rules, could be ignored or flagged.
        
        print("Sync complete.")

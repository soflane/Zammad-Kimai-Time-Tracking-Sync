from typing import List, Dict, Optional
from enum import Enum

from app.connectors.base import TimeEntryNormalized

class ReconciliationStatus(str, Enum):
    MATCH = "match"
    CONFLICT = "conflict"
    MISSING_IN_KIMAI = "missing_in_kimai"
    MISSING_IN_ZAMMAD = "missing_in_zammad" # Though not primary sync direction, useful for full picture

class ReconciledTimeEntry(TimeEntryNormalized):
    """
    Extends TimeEntryNormalized with reconciliation status and references to other entries.
    """
    reconciliation_status: ReconciliationStatus
    # Optional references to corresponding entries in other systems
    kimai_entry: Optional[TimeEntryNormalized] = None
    zammad_entry: Optional[TimeEntryNormalized] = None

class ReconciliationService:
    """
    Service responsible for reconciling time entries between Zammad and Kimai.
    Identifies matches, conflicts, and missing entries based on defined rules.
    """

    def __init__(self):
        pass # No external dependencies for core logic yet

    def _is_exact_match(self, zammad_entry: TimeEntryNormalized, kimai_entry: TimeEntryNormalized) -> bool:
        """
        Checks for an exact match between two normalized time entries.
        Criteria: same source_id (if available from previous sync), or same ticket, date, and time.
        """
        if zammad_entry.source_id and kimai_entry.source_id and zammad_entry.source_id == kimai_entry.source_id:
            return True # Assume source_id means they are the same entry across systems
        
        # Primary matching: ticket_id/number, entry_date, and duration
        if (zammad_entry.ticket_id == kimai_entry.ticket_id or 
            zammad_entry.ticket_number == kimai_entry.ticket_number) and \
           zammad_entry.entry_date == kimai_entry.entry_date and \
           abs(zammad_entry.time_minutes - kimai_entry.time_minutes) < 1.0: # Allow small discrepancies (e.g., floating point)
            return True
        return False

    def _is_conflict(self, zammad_entry: TimeEntryNormalized, kimai_entry: TimeEntryNormalized) -> bool:
        """
        Checks if two entries are likely referring to the same work but have different values.
        This is a heuristic and can be refined.
        """
        # More flexible matching for potential conflicts: similar ticket, date, but different times
        if (zammad_entry.ticket_id == kimai_entry.ticket_id or 
            zammad_entry.ticket_number == kimai_entry.ticket_number) and \
           zammad_entry.entry_date == kimai_entry.entry_date and \
           abs(zammad_entry.time_minutes - kimai_entry.time_minutes) >= 1.0:
            return True
        return False


    async def reconcile_entries(
        self,
        zammad_entries: List[TimeEntryNormalized],
        kimai_entries: List[TimeEntryNormalized]
    ) -> List[ReconciledTimeEntry]:
        """
        Reconciles a list of normalized Zammad entries against Kimai entries.
        Returns a list of ReconciledTimeEntry indicating status and linking related entries.
        """
        reconciled_results: List[ReconciledTimeEntry] = []
        unmatched_kimai_entries = {entry.source_id: entry for entry in kimai_entries}

        for z_entry in zammad_entries:
            found_match = False
            for k_id, k_entry in list(unmatched_kimai_entries.items()): # Iterate over copy to allow deletion
                if self._is_exact_match(z_entry, k_entry):
                    reconciled_results.append(ReconciledTimeEntry(
                        **z_entry.model_dump(),
                        reconciliation_status=ReconciliationStatus.MATCH,
                        kimai_entry=k_entry,
                        zammad_entry=z_entry
                    ))
                    del unmatched_kimai_entries[k_id]
                    found_match = True
                    break
                elif self._is_conflict(z_entry, k_entry):
                    reconciled_results.append(ReconciledTimeEntry(
                        **z_entry.model_dump(),
                        reconciliation_status=ReconciliationStatus.CONFLICT,
                        kimai_entry=k_entry,
                        zammad_entry=z_entry
                    ))
                    del unmatched_kimai_entries[k_id]
                    found_match = True
                    break
            
            if not found_match:
                reconciled_results.append(ReconciledTimeEntry(
                    **z_entry.model_dump(),
                    reconciliation_status=ReconciliationStatus.MISSING_IN_KIMAI,
                    zammad_entry=z_entry
                ))
        
        # Add any remaining unmatched Kimai entries
        for k_entry in unmatched_kimai_entries.values():
            reconciled_results.append(ReconciledTimeEntry(
                **k_entry.model_dump(),
                reconciliation_status=ReconciliationStatus.MISSING_IN_ZAMMAD,
                kimai_entry=k_entry
            ))

        return reconciled_results

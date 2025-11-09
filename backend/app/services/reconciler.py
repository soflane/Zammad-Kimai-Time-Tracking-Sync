from typing import List, Dict, Optional, TYPE_CHECKING
from enum import Enum
from datetime import datetime, date

from app.connectors.base import TimeEntryNormalized
import logging

if TYPE_CHECKING:
    from app.connectors.kimai_connector import KimaiConnector

log = logging.getLogger(__name__)

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
    
    Supports rounding-aware matching when KimaiConnector is provided.
    """

    def __init__(self, kimai_connector: Optional['KimaiConnector'] = None):
        """
        Initialize reconciliation service.
        
        Args:
            kimai_connector: Optional KimaiConnector for rounding-aware matching
        """
        self.kimai_connector = kimai_connector

    def _is_exact_match(self, zammad_entry: TimeEntryNormalized, kimai_entry: TimeEntryNormalized) -> bool:
        """
        Checks for an exact match between two normalized time entries.
        Criteria: same source_id (if available from previous sync), or same ticket, date, and time.
        
        When KimaiConnector is available, applies Kimai's rounding rules to Zammad entry
        before comparison for more accurate matching.
        """
        log.debug(f"Matching check: Zammad {zammad_entry.source_id} (ticket: {zammad_entry.ticket_number}, begin: {zammad_entry.begin_time}, dur: {zammad_entry.duration_sec}) vs Kimai {kimai_entry.source_id} (ticket: {kimai_entry.ticket_number}, begin: {kimai_entry.begin_time}, dur: {kimai_entry.duration_sec})")
        
        # Exact source_id (from zid tag or marker)
        if zammad_entry.source_id and kimai_entry.source_id and zammad_entry.source_id == kimai_entry.source_id:
            log.debug(" -> Exact match on source_id")
            return True
        
        # Rounding-aware matching (if Kimai connector available)
        if self.kimai_connector and zammad_entry.begin_time and zammad_entry.entry_date:
            try:
                z_begin_dt = datetime.fromisoformat(zammad_entry.begin_time)
                z_date = date.fromisoformat(zammad_entry.entry_date)
                
                # Apply Kimai rounding to Zammad times
                rounded_begin, rounded_duration = self.kimai_connector.apply_rounding_rules(
                    z_begin_dt,
                    zammad_entry.duration_sec,
                    z_date
                )
                
                rounded_begin_str = rounded_begin.strftime('%Y-%m-%dT%H:%M:%S')
                
                # Compare rounded Zammad vs actual Kimai
                if (zammad_entry.ticket_number == kimai_entry.ticket_number and
                    rounded_begin_str == kimai_entry.begin_time and
                    abs(rounded_duration - kimai_entry.duration_sec) <= 60):
                    log.debug(f" -> Match after applying Kimai rounding rules (rounded begin: {rounded_begin_str}, rounded dur: {rounded_duration}s)")
                    return True
            except Exception as e:
                log.warning(f"Failed to apply rounding rules for matching: {e}")
                # Continue with non-rounded matching below
        
        # Exact on ticket_number + begin_time + duration (±60s)
        if (zammad_entry.ticket_number == kimai_entry.ticket_number and
            zammad_entry.begin_time == kimai_entry.begin_time and
            abs(zammad_entry.duration_sec - kimai_entry.duration_sec) <= 60):
            log.debug(" -> Exact match on ticket + begin_time + duration")
            return True
        
        # Fallback: ticket + entry_date + duration (<1 min diff)
        if (zammad_entry.ticket_number == kimai_entry.ticket_number and
            zammad_entry.entry_date == kimai_entry.entry_date and
            abs((zammad_entry.duration_sec / 60) - (kimai_entry.duration_sec / 60)) < 1.0):
            log.debug(" -> Match on fallback: ticket + date + duration")
            return True
        
        log.debug(" -> No match")
        return False

    def _is_conflict(self, zammad_entry: TimeEntryNormalized, kimai_entry: TimeEntryNormalized) -> bool:
        """
        Checks if two entries are likely referring to the same work but have different values.
        This is a heuristic and can be refined.
        """
        log.debug(f"Conflict check: Zammad {zammad_entry.source_id} vs Kimai {kimai_entry.source_id}")
        
        # Loose match on ticket + begin_time but duration diff >60s
        if (zammad_entry.ticket_number == kimai_entry.ticket_number and
            zammad_entry.begin_time == kimai_entry.begin_time and
            abs(zammad_entry.duration_sec - kimai_entry.duration_sec) > 60):
            log.debug(" -> Conflict on ticket + begin_time, duration mismatch")
            return True
        
        # Fallback loose: ticket + date, duration >=1 min diff
        if (zammad_entry.ticket_number == kimai_entry.ticket_number and
            zammad_entry.entry_date == kimai_entry.entry_date and
            abs((zammad_entry.duration_sec / 60) - (kimai_entry.duration_sec / 60)) >= 1.0):
            log.debug(" -> Conflict on fallback: ticket + date, duration diff")
            return True
        
        log.debug(" -> No conflict")
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
                # Log potential near-misses for debugging
                if z_entry.ticket_number == k_entry.ticket_number:
                    log.debug(f"Near miss on ticket {z_entry.ticket_number}: date {z_entry.entry_date} vs {k_entry.entry_date}, begin {z_entry.begin_time} vs {k_entry.begin_time}, dur {z_entry.duration_sec} vs {k_entry.duration_sec}")
            
            if not found_match:
                log.debug(f"No match for Zammad {z_entry.source_id} (ticket {z_entry.ticket_number}, date {z_entry.entry_date})")
            
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

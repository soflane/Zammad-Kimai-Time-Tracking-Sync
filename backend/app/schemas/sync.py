from datetime import date
from typing import Optional, List
from pydantic import BaseModel

class SyncRequest(BaseModel):
    start_date: Optional[str] = None  # YYYY-MM-DD, use last 30 days if not provided
    end_date: Optional[str] = None    # YYYY-MM-DD, use today if not provided

class SyncResponse(BaseModel):
    status: str  # 'success', 'failed'
    message: str
    start_date: str
    end_date: str
    num_processed: int = 0
    num_created: int = 0
    num_conflicts: int = 0
    num_skipped: int = 0
    error_detail: Optional[str] = None  # Detailed error message when status is 'failed'

class SyncRunResponse(BaseModel):
    id: int
    trigger_type: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    status: str
    entries_fetched: Optional[int] = None
    entries_synced: Optional[int] = None
    entries_already_synced: Optional[int] = None
    entries_skipped: Optional[int] = None
    entries_failed: Optional[int] = None
    conflicts_detected: Optional[int] = None
    error_message: Optional[str] = None

class PaginatedSyncRuns(BaseModel):
    data: List[SyncRunResponse]
    total: int

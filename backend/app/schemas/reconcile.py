from typing import Optional, List, Literal
from pydantic import BaseModel


class WorklogData(BaseModel):
    """Represents time tracking data from source or target system."""
    minutes: int
    activity: str
    user: str
    startedAt: str


class AutoPath(BaseModel):
    """Indicates which entities need to be auto-created in Kimai."""
    createCustomer: Optional[bool] = None
    createProject: Optional[bool] = None
    createTimesheet: Optional[bool] = None


class DiffItem(BaseModel):
    """
    Reconciliation diff item representing a conflict or missing entry.
    Maps Zammad ticket → Kimai project with customer and timesheet details.
    """
    id: str
    status: Literal['missing', 'conflict']
    ticketId: str  # e.g., "#2842"
    ticketTitle: str  # project title in Kimai
    customer: str  # aggregated customer name
    source: Optional[WorklogData] = None  # Zammad worklog
    target: Optional[WorklogData] = None  # Kimai timesheet
    autoPath: Optional[AutoPath] = None  # Auto-creation indicators


class ReconcileResponse(BaseModel):
    """Paginated response for reconcile diff items."""
    items: List[DiffItem]
    total: int
    counts: dict  # {"conflicts": int, "missing": int}


class RowActionRequest(BaseModel):
    """Request body for performing action on a reconcile row."""
    op: Literal['keep-target', 'update', 'create', 'skip']

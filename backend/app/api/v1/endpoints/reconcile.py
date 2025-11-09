from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.conflict import Conflict as DBConflict
from app.schemas.reconcile import (
    DiffItem,
    ReconcileResponse,
    RowActionRequest,
    WorklogData,
    AutoPath
)
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.connectors.kimai_connector import KimaiConnector
from app.models.connector import Connector as DBConnector
from app.utils.encrypt import decrypt_data

router = APIRouter()
log = logging.getLogger(__name__)


async def _compute_autopath(
    conflict: DBConflict,
    kimai_connector: KimaiConnector
) -> AutoPath:
    """
    Compute which entities need to be auto-created in Kimai.
    Checks customer and project existence based on Zammad data.
    """
    autopath = AutoPath()
    
    # Extract organization ID from Zammad data
    zammad_data = conflict.zammad_data or {}
    org_id = zammad_data.get('organization_id')
    org_name = zammad_data.get('organization')
    
    # Check if customer exists
    customer_exists = False
    if org_id:
        try:
            customer = await kimai_connector.find_customer_by_number(f"ZAM-ORG-{org_id}")
            customer_exists = customer is not None
        except Exception as e:
            log.debug(f"Customer lookup failed: {e}")
    
    # Fallback to name search if no org_id match
    if not customer_exists and org_name:
        try:
            customer = await kimai_connector.find_customer(org_name)
            customer_exists = customer is not None
        except Exception as e:
            log.debug(f"Customer name lookup failed: {e}")
    
    autopath.createCustomer = not customer_exists
    
    # Check if project exists
    ticket_number = conflict.ticket_number
    project_exists = False
    if ticket_number:
        try:
            project = await kimai_connector.find_project_by_number(ticket_number.strip('#'))
            project_exists = project is not None
        except Exception as e:
            log.debug(f"Project lookup failed: {e}")
    
    autopath.createProject = not project_exists
    
    # Timesheet creation needed for missing entries
    autopath.createTimesheet = conflict.conflict_type in ['missing_in_kimai', 'missing']
    
    return autopath


def _conflict_to_diffitem(conflict: DBConflict, autopath: Optional[AutoPath] = None) -> DiffItem:
    """Transform Conflict model to DiffItem schema."""
    zammad_data = conflict.zammad_data or {}
    kimai_data = conflict.kimai_data or {}
    
    # Extract source (Zammad) data
    source = None
    if zammad_data:
        source = WorklogData(
            minutes=conflict.zammad_time_minutes or zammad_data.get('time_unit', 0),
            activity=conflict.activity_name or zammad_data.get('activity_name', 'Unknown'),
            user=zammad_data.get('user_email', 'Unknown'),
            startedAt=conflict.zammad_created_at or zammad_data.get('created_at', '')
        )
    
    # Extract target (Kimai) data
    target = None
    if kimai_data and conflict.conflict_type == 'conflict':
        target = WorklogData(
            minutes=conflict.kimai_duration_minutes or 0,
            activity=kimai_data.get('activity_name', 'Unknown'),
            user=kimai_data.get('user_email', 'Unknown'),
            startedAt=conflict.kimai_begin or kimai_data.get('begin', '')
        )
    
    return DiffItem(
        id=str(conflict.id),
        status='conflict' if conflict.conflict_type == 'conflict' else 'missing',
        ticketId=conflict.ticket_number or '#Unknown',
        ticketTitle=conflict.project_name or zammad_data.get('ticket_title', 'Unknown'),
        customer=conflict.customer_name or zammad_data.get('organization', 'Unknown Customer'),
        source=source,
        target=target,
        autoPath=autopath
    )


@router.get("/", response_model=ReconcileResponse)
async def get_reconcile_diff(
    filter: str = Query('conflicts', regex='^(conflicts|missing)$'),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """
    Get reconciliation diff items filtered by type.
    Returns conflicts or missing entries with auto-creation indicators.
    """
    # Get active Kimai connector for autoPath computation
    kimai_connector_db = db.query(DBConnector).filter(
        DBConnector.type == 'kimai',
        DBConnector.is_active == True
    ).first()
    
    kimai_connector = None
    if kimai_connector_db:
        try:
            decrypted_token = decrypt_data(kimai_connector_db.api_token)
            kimai_connector = KimaiConnector(
                base_url=kimai_connector_db.base_url,
                api_token=decrypted_token,
                settings=kimai_connector_db.settings or {}
            )
        except Exception as e:
            log.error(f"Failed to initialize Kimai connector: {e}")
    
    # Build query based on filter
    query = db.query(DBConflict).filter(DBConflict.resolution_status == 'open')
    
    if filter == 'conflicts':
        query = query.filter(DBConflict.conflict_type == 'conflict')
    elif filter == 'missing':
        query = query.filter(DBConflict.conflict_type.in_(['missing_in_kimai', 'missing_in_zammad', 'missing']))
    
    # Get counts for both types
    conflicts_count = db.query(DBConflict).filter(
        DBConflict.resolution_status == 'open',
        DBConflict.conflict_type == 'conflict'
    ).count()
    
    missing_count = db.query(DBConflict).filter(
        DBConflict.resolution_status == 'open',
        DBConflict.conflict_type.in_(['missing_in_kimai', 'missing_in_zammad', 'missing'])
    ).count()
    
    # Get total for current filter
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * pageSize
    conflicts = query.offset(offset).limit(pageSize).all()
    
    # Transform to DiffItems with autoPath computation
    items: List[DiffItem] = []
    for conflict in conflicts:
        autopath = None
        if kimai_connector and conflict.conflict_type in ['missing_in_kimai', 'missing']:
            try:
                autopath = await _compute_autopath(conflict, kimai_connector)
            except Exception as e:
                log.error(f"AutoPath computation failed for conflict {conflict.id}: {e}")
        
        items.append(_conflict_to_diffitem(conflict, autopath))
    
    return ReconcileResponse(
        items=items,
        total=total,
        counts={
            "conflicts": conflicts_count,
            "missing": missing_count
        }
    )


@router.post("/row/{row_id}", status_code=status.HTTP_200_OK)
async def perform_row_action(
    row_id: str,
    action: RowActionRequest,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """
    Perform action on a reconcile row (conflict or missing entry).
    Actions: keep-target, update, create, skip
    """
    # Find the conflict
    conflict = db.query(DBConflict).filter(DBConflict.id == int(row_id)).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Perform action based on operation
    if action.op == 'keep-target':
        # Mark as resolved, keep Kimai data as-is
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'keep_target'
        conflict.notes = 'User chose to keep target (Kimai) data'
        
    elif action.op == 'update':
        # Update Kimai timesheet from Zammad data
        # This would trigger actual sync service update
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'update_from_source'
        conflict.notes = 'User chose to update Kimai from Zammad data'
        # TODO: Trigger actual Kimai update via sync service
        
    elif action.op == 'create':
        # Create customer/project/timesheet in Kimai
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'create_in_target'
        conflict.notes = 'User chose to create missing entities in Kimai'
        # TODO: Trigger actual creation via sync service
        
    elif action.op == 'skip':
        # Mark as resolved but skip action
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'skipped'
        conflict.notes = 'User chose to skip this entry'
    
    db.commit()
    db.refresh(conflict)
    
    return {
        "status": "success",
        "message": f"Action '{action.op}' performed successfully",
        "conflict_id": conflict.id
    }

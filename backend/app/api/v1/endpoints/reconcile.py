from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

from app.database import get_db
from app.models.conflict import Conflict as DBConflict
from app.models.time_entry import TimeEntry
from app.models.mapping import ActivityMapping
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
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.base import TimeEntryNormalized
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
    """Transform Conflict model to DiffItem schema extracting data from JSONB and flat fields."""
    # Extract Zammad data
    zammad_data = conflict.zammad_data or {}
    kimai_data = conflict.kimai_data or {}
    
    # Extract source (Zammad) worklog data
    source = None
    if conflict.zammad_time_minutes is not None or zammad_data:
        # Extract user from JSONB
        user = (zammad_data.get('user_name') or 
                zammad_data.get('user_email') or 
                zammad_data.get('customer_name') or
                'Unknown User')
        
        # Extract activity from JSONB or flat field
        activity = (conflict.activity_name or 
                   zammad_data.get('activity_type_name') or 
                   zammad_data.get('activity') or
                   'Unknown Activity')
        
        # Extract description
        description = (zammad_data.get('description') or 
                      zammad_data.get('ticket_title') or 
                      None)
        
        source = WorklogData(
            minutes=conflict.zammad_time_minutes or 0,
            activity=activity,
            user=user,
            startedAt=str(conflict.zammad_created_at) if conflict.zammad_created_at else '',
            ticketNumber=conflict.ticket_number,
            description=description
        )
    
    # Extract target (Kimai) timesheet data
    target = None
    if conflict.kimai_duration_minutes is not None and conflict.conflict_type in ['duplicate', 'conflict', 'unmapped_activity']:
        # Extract from Kimai JSONB
        kimai_user = (kimai_data.get('user_name') or 
                     kimai_data.get('user') or 
                     'Unknown User')
        
        kimai_activity = (kimai_data.get('activity_name') or 
                         kimai_data.get('activity') or 
                         'Unknown Activity')
        
        kimai_description = kimai_data.get('description')
        
        target = WorklogData(
            minutes=conflict.kimai_duration_minutes or 0,
            activity=kimai_activity,
            user=kimai_user,
            startedAt=str(conflict.kimai_begin) if conflict.kimai_begin else '',
            ticketNumber=conflict.ticket_number,
            description=kimai_description
        )
    
    # Build conflict reason message
    conflict_reason = None
    if conflict.reason_detail:
        conflict_reason = conflict.reason_detail
    elif conflict.reason_code and conflict.reason_code != 'OTHER':
        # Humanize reason code
        conflict_reason = conflict.reason_code.replace('_', ' ').title()
    
    return DiffItem(
        id=str(conflict.id),
        status='conflict' if conflict.conflict_type in ['duplicate', 'conflict', 'unmapped_activity'] else 'missing',
        ticketId=conflict.ticket_number or '#Unknown',
        ticketTitle=conflict.project_name or zammad_data.get('ticket_title') or 'Unknown',
        customer=conflict.customer_name or zammad_data.get('organization') or 'Unknown Customer',
        source=source,
        target=target,
        autoPath=autopath,
        conflictReason=conflict_reason,
        reasonCode=conflict.reason_code
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
    
    # Build query based on filter (use 'pending' not 'open')
    query = db.query(DBConflict).filter(DBConflict.resolution_status == 'pending')
    
    if filter == 'conflicts':
        query = query.filter(DBConflict.conflict_type.in_(['conflict', 'duplicate', 'unmapped_activity']))
    elif filter == 'missing':
        query = query.filter(DBConflict.conflict_type.in_(['missing', 'missing_in_kimai', 'missing_in_zammad', 'create_failed']))
    
    # Get counts for both types
    conflicts_count = db.query(DBConflict).filter(
        DBConflict.resolution_status == 'pending',
        DBConflict.conflict_type.in_(['conflict', 'duplicate', 'unmapped_activity'])
    ).count()
    
    missing_count = db.query(DBConflict).filter(
        DBConflict.resolution_status == 'pending',
        DBConflict.conflict_type.in_(['missing', 'missing_in_kimai', 'missing_in_zammad', 'create_failed'])
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
        if kimai_connector and conflict.conflict_type in ['missing_in_kimai', 'missing', 'create_failed']:
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
    
    For 'create' and 'update' operations, actually performs the Kimai API calls.
    """
    # Find the conflict
    conflict = db.query(DBConflict).filter(DBConflict.id == int(row_id)).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    # Get Kimai connector for create/update operations
    kimai_connector = None
    if action.op in ['create', 'update']:
        kimai_connector_db = db.query(DBConnector).filter(
            DBConnector.type == 'kimai',
            DBConnector.is_active == True
        ).first()
        
        if not kimai_connector_db:
            raise HTTPException(status_code=400, detail="No active Kimai connector found")
        
        try:
            decrypted_token = decrypt_data(kimai_connector_db.api_token)
            kimai_connector = KimaiConnector(
                base_url=kimai_connector_db.base_url,
                api_token=decrypted_token,
                settings=kimai_connector_db.settings or {}
            )
        except Exception as e:
            log.error(f"Failed to initialize Kimai connector: {e}")
            raise HTTPException(status_code=500, detail=f"Kimai connector initialization failed: {str(e)}")
    
    # Perform action based on operation
    if action.op == 'keep-target':
        # Mark as resolved, keep Kimai data as-is
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'keep_target'
        conflict.resolved_at = datetime.now(ZoneInfo('Europe/Brussels'))
        conflict.resolved_by = current_user.username if current_user else 'system'
        conflict.notes = 'User chose to keep target (Kimai) data'
        
    elif action.op == 'update':
        # Update Kimai timesheet from Zammad data
        zammad_data = conflict.zammad_data or {}
        if not conflict.kimai_id:
            raise HTTPException(status_code=400, detail="No Kimai timesheet ID found for update")
        
        try:
            # Get activity mapping
            activity_type_id = zammad_data.get('activity_type_id')
            if not activity_type_id:
                raise HTTPException(status_code=400, detail="No activity type ID in Zammad data")
            
            mapping = db.query(ActivityMapping).filter(
                ActivityMapping.zammad_type_id == activity_type_id
            ).first()
            
            if not mapping:
                raise HTTPException(status_code=400, detail=f"No activity mapping found for Zammad type {activity_type_id}")
            
            # Prepare update payload
            begin_time = conflict.zammad_created_at.strftime('%Y-%m-%dT%H:%M:%S') if conflict.zammad_created_at else None
            duration_sec = int((conflict.zammad_time_minutes or 0) * 60)
            
            if not begin_time:
                raise HTTPException(status_code=400, detail="Missing begin time in Zammad data")
            
            # Calculate end time
            begin_dt = datetime.fromisoformat(begin_time)
            end_dt = begin_dt + timedelta(seconds=duration_sec)
            
            update_payload = {
                "activity": mapping.kimai_activity_id,
                "begin": begin_time,
                "end": end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                "description": zammad_data.get('description', '')
            }
            
            # Perform update
            await kimai_connector._request("PATCH", f"/api/timesheets/{conflict.kimai_id}", json=update_payload)
            
            conflict.resolution_status = 'resolved'
            conflict.resolution_action = 'update_from_source'
            conflict.resolved_at = datetime.now(ZoneInfo('Europe/Brussels'))
            conflict.resolved_by = current_user.username if current_user else 'system'
            conflict.notes = f'Updated Kimai timesheet {conflict.kimai_id} from Zammad data'
            
            log.info(f"Updated Kimai timesheet {conflict.kimai_id} from conflict {conflict.id}")
            
        except Exception as e:
            log.error(f"Failed to update Kimai timesheet: {e}")
            raise HTTPException(status_code=500, detail=f"Kimai update failed: {str(e)}")
        
    elif action.op == 'create':
        # Create customer/project/timesheet in Kimai
        zammad_data = conflict.zammad_data or {}
        kimai_config = kimai_connector.config.get('settings', {})
        
        try:
            # 1. Ensure customer exists
            customer_name = conflict.customer_name or zammad_data.get('organization', 'Unknown Customer')
            org_id = zammad_data.get('organization_id')
            external_id = f"OID-{org_id}" if org_id else None
            
            customer = None
            if external_id:
                customer = await kimai_connector.find_customer_by_number(external_id)
            if not customer:
                customer = await kimai_connector.find_customer_by_name_exact(customer_name)
            
            if not customer:
                # Create customer
                customer_payload = {
                    "name": customer_name,
                    "number": external_id or "",
                    "country": kimai_config.get('default_country', 'BE'),
                    "currency": kimai_config.get('default_currency', 'EUR'),
                    "timezone": kimai_config.get('default_timezone', 'Europe/Brussels'),
                    "visible": True,
                    "billable": True
                }
                customer = await kimai_connector.create_customer(customer_payload)
                log.info(f"Created customer '{customer_name}' (ID: {customer['id']}) for conflict {conflict.id}")
            
            # 2. Ensure project exists
            ticket_number = conflict.ticket_number or zammad_data.get('ticket_number', '#Unknown')
            ticket_id = zammad_data.get('ticket_id')
            project_name = f"Ticket-{ticket_number.lstrip('#')}"
            project_external_id = f"TID-{ticket_id}" if ticket_id else None
            
            project = None
            if project_external_id:
                project = await kimai_connector.find_project_by_number(customer['id'], project_external_id)
            if not project:
                project = await kimai_connector.find_project(customer['id'], ticket_number)
            
            if not project:
                # Create project
                project_payload = {
                    "name": project_name,
                    "customer": customer['id'],
                    "number": project_external_id or ""
                }
                project = await kimai_connector.create_project(project_payload)
                
                # Enable global activities
                await kimai_connector.patch_project(project['id'], {"globalActivities": True, "visible": True})
                log.info(f"Created project '{project_name}' (ID: {project['id']}) for conflict {conflict.id}")
            
            # 3. Get activity mapping
            activity_type_id = zammad_data.get('activity_type_id')
            if not activity_type_id:
                raise HTTPException(status_code=400, detail="No activity type ID in Zammad data")
            
            mapping = db.query(ActivityMapping).filter(
                ActivityMapping.zammad_type_id == activity_type_id
            ).first()
            
            if not mapping:
                raise HTTPException(status_code=400, detail=f"No activity mapping found for Zammad type {activity_type_id}")
            
            # 4. Create timesheet
            begin_time = conflict.zammad_created_at.strftime('%Y-%m-%dT%H:%M:%S') if conflict.zammad_created_at else None
            duration_sec = int((conflict.zammad_time_minutes or 0) * 60)
            
            if not begin_time:
                raise HTTPException(status_code=400, detail="Missing begin time in Zammad data")
            
            begin_dt = datetime.fromisoformat(begin_time)
            end_dt = begin_dt + timedelta(seconds=duration_sec)
            
            # Get Zammad connector for URL
            zammad_connector_db = db.query(DBConnector).filter(
                DBConnector.type == 'zammad',
                DBConnector.is_active == True
            ).first()
            zammad_base_url = zammad_connector_db.base_url if zammad_connector_db else "https://zammad.example.com"
            
            source_id = zammad_data.get('source_id', 'unknown')
            zammad_url = f"{zammad_base_url.rstrip('/')}/#ticket/zoom/{ticket_id}" if ticket_id else ""
            
            description = f"""ZAM:T{ticket_id}|TA:{source_id}
Ticket-{ticket_number.lstrip('#')}
Zammad Ticket ID: {ticket_id}
Time Accounting ID: {source_id}
Customer: {customer_name}
Title: {zammad_data.get('ticket_title', 'N/A')}
Zammad URL: {zammad_url}
{zammad_data.get('description', '')}"""
            
            timesheet_payload = {
                "project": project['id'],
                "activity": mapping.kimai_activity_id,
                "begin": begin_time,
                "end": end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                "description": description,
                "tags": "source:zammad"
            }
            
            timesheet = await kimai_connector.create_timesheet(timesheet_payload)
            
            # Update conflict and related TimeEntry
            conflict.resolution_status = 'resolved'
            conflict.resolution_action = 'create_in_target'
            conflict.resolved_at = datetime.now(ZoneInfo('Europe/Brussels'))
            conflict.resolved_by = current_user.username if current_user else 'system'
            conflict.kimai_id = timesheet['id']
            conflict.notes = f'Created Kimai timesheet {timesheet["id"]} (customer: {customer["id"]}, project: {project["id"]})'
            
            # Update TimeEntry if exists
            if conflict.time_entry_id:
                time_entry = db.query(TimeEntry).get(conflict.time_entry_id)
                if time_entry:
                    time_entry.kimai_id = timesheet['id']
                    time_entry.synced_at = datetime.now(ZoneInfo('Europe/Brussels'))
                    time_entry.sync_status = 'synced'
                    time_entry.updated_at = datetime.now(ZoneInfo('Europe/Brussels'))
            
            log.info(f"Created Kimai timesheet {timesheet['id']} for conflict {conflict.id}")
            
        except Exception as e:
            log.error(f"Failed to create Kimai entities: {e}")
            raise HTTPException(status_code=500, detail=f"Kimai creation failed: {str(e)}")
        
    elif action.op == 'skip':
        # Mark as resolved but skip action
        conflict.resolution_status = 'resolved'
        conflict.resolution_action = 'skipped'
        conflict.resolved_at = datetime.now(ZoneInfo('Europe/Brussels'))
        conflict.resolved_by = current_user.username if current_user else 'system'
        conflict.notes = 'User chose to skip this entry'
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {action.op}")
    
    db.commit()
    db.refresh(conflict)
    
    return {
        "status": "success",
        "message": f"Action '{action.op}' performed successfully",
        "conflict_id": conflict.id
    }

from typing import Annotated, Optional
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sync_service import SyncService
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService
from app.models.connector import Connector as DBConnector
from app.models.sync_run import SyncRun
from app.schemas.sync import SyncRequest, SyncResponse
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.utils.encrypt import decrypt_data
from app.models.conflict import Conflict
from app.utils.audit_logger import create_audit_log
from sqlalchemy import func, or_
from datetime import timedelta
from zoneinfo import ZoneInfo
from fastapi.responses import Response
import csv
from io import StringIO

log = logging.getLogger(__name__)
router = APIRouter()

@router.post("/run", response_model=SyncResponse)
async def run_sync(
    http_request: Request,
    request: SyncRequest = Depends(),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Trigger a manual sync run with optional date range."""
    # Resolve dates
    end_d = date.today().isoformat() if not request.end_date else request.end_date
    start_d = (date.today() - timedelta(days=30)).isoformat() if not request.start_date else request.start_date
    
    # Log sync trigger
    create_audit_log(
        db=db,
        request=http_request,
        action="sync_triggered",
        user=current_user.username if current_user else None,
        details={"start_date": start_d, "end_date": end_d, "trigger_type": "manual"}
    )
    
    # Fetch active connectors once
    zammad_conn = db.query(DBConnector).filter(DBConnector.type == "zammad", DBConnector.is_active == True).first()
    kimai_conn = db.query(DBConnector).filter(DBConnector.type == "kimai", DBConnector.is_active == True).first()
    
    if not zammad_conn or not kimai_conn:
        # Create SyncRun for no connectors case
        sync_run = SyncRun(
            trigger_type='manual',
            start_time=datetime.now(ZoneInfo('Europe/Brussels')),
            status='failed',
            error_message="No active Zammad and Kimai connectors configured",
            entries_synced=0,
            entries_failed=1,
            conflicts_detected=0
        )
        db.add(sync_run)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active Zammad and Kimai connectors must be configured and active."
        )
    
    import traceback

    log.info(f"Sync request received for {start_d} to {end_d}")
    
    # Decrypt tokens
    zammad_token = decrypt_data(zammad_conn.api_token)
    kimai_token = decrypt_data(kimai_conn.api_token)
    
    # Create SyncRun for manual sync early
    sync_run = SyncRun(
        trigger_type='manual',
        start_time=datetime.now(ZoneInfo('Europe/Brussels')),
        status='running'
    )
    db.add(sync_run)
    db.commit()
    sync_run_id = sync_run.id
    
    log.info(f"Sync request received for {start_d} to {end_d}, run_id: {sync_run_id}")
    
    # Instantiate connectors properly with settings (same pattern as get_connector_instance)
    log.debug("Instantiating Zammad connector")
    zammad_config = {
        "base_url": str(zammad_conn.base_url),
        "api_token": zammad_token,
        "settings": zammad_conn.settings or {}
    }
    zammad_instance = ZammadConnector(zammad_config)
    
    log.debug("Instantiating Kimai connector")
    kimai_config = {
        "base_url": str(kimai_conn.base_url),
        "api_token": kimai_token,
        "settings": kimai_conn.settings or {}
    }
    kimai_instance = KimaiConnector(kimai_config)
    
    normalizer = NormalizerService()
    reconciler = ReconciliationService()
    
    sync_service = SyncService(
        zammad_connector=zammad_instance,
        kimai_connector=kimai_instance,
        normalizer_service=normalizer,
        reconciliation_service=reconciler,
        db=db
    )

    try:
        log.info(f"Starting sync process for period {start_d} to {end_d}, run_id: {sync_run_id}")
        stats = await sync_service.sync_time_entries(start_d, end_d, sync_run, trigger_type='manual')
        
        log.info(f"Sync completed: processed={stats['processed']}, created={stats['created']}, skipped={stats['skipped']}, conflicts={stats['conflicts']}")
        return SyncResponse(
            status="success",
            message=f"Successfully synced {stats['created']} entries",
            start_date=start_d,
            end_date=end_d,
            num_processed=stats["processed"],
            num_created=stats["created"],
            num_skipped=stats["skipped"],
            num_conflicts=stats["conflicts"]
        )
    except ValueError as ve:
        # ValueError is raised by sync_service with user-friendly error messages
        error_msg = str(ve)
        log.error(f"Sync failed: {error_msg}")
        
        return SyncResponse(
            status="failed",
            message="Sync failed",
            start_date=start_d,
            end_date=end_d,
            num_processed=0,
            num_created=0,
            num_skipped=0,
            num_conflicts=0,
            error_detail=error_msg
        )
    except Exception as e:
        # Unexpected errors - should be rare after sync_service improvements
        error_msg = f"Unexpected error: {str(e)}"
        log.error(f"Unexpected error during sync: {error_msg}")
        log.debug(f"Stack trace: {traceback.format_exc()}")
        
        return SyncResponse(
            status="failed",
            message="Sync failed",
            start_date=start_d,
            end_date=end_d,
            num_processed=0,
            num_created=0,
            num_skipped=0,
            num_conflicts=0,
            error_detail=error_msg
        )

@router.get("/runs", response_model=list[dict])
async def get_sync_runs(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve history of sync runs."""
    q = db.query(SyncRun).order_by(SyncRun.start_time.desc())
    if status and status != "all":
        q = q.filter(SyncRun.status == status)
    if start_date:
        q = q.filter(SyncRun.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        q = q.filter(SyncRun.start_time <= datetime.fromisoformat(end_date + 'T23:59:59'))
    if search:
        q = q.filter(
            or_(
                SyncRun.id.like(f"%{search}%"),
                SyncRun.error_message.like(f"%{search}%")
            )
        )
    sync_runs = q.offset(skip).limit(limit).all()
    return [
        {
            "id": sr.id,
            "trigger_type": sr.trigger_type,
            "started_at": sr.start_time.isoformat() if sr.start_time else None,
            "ended_at": sr.end_time.isoformat() if sr.end_time else None,
            "status": sr.status,
            "entries_fetched": sr.entries_fetched,
            "entries_synced": sr.entries_synced,
            "entries_already_synced": sr.entries_already_synced,
            "entries_skipped": sr.entries_skipped,
            "entries_failed": sr.entries_failed,
            "conflicts_detected": sr.conflicts_detected,
            "error_message": sr.error_message
        }
        for sr in sync_runs
    ]


@router.get("/kpi")
async def get_kpi(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Get KPI data for dashboard: open conflicts, last sync, weekly synced minutes."""
    # Open conflicts count
    open_conflicts = db.query(Conflict).filter(Conflict.resolution_status != 'resolved').count()

    # Last sync
    latest_sync = db.query(SyncRun).order_by(SyncRun.start_time.desc()).first()
    last_sync = latest_sync.start_time.isoformat() if latest_sync else None

    # Weekly synced minutes: sum(time_minutes) group by entry_date for last 7 days where sync_status = 'synced'
    from app.models.time_entry import TimeEntry
    seven_days_ago = datetime.now(ZoneInfo('Europe/Brussels')) - timedelta(days=7)
    weekly_data = db.query(
        func.date(TimeEntry.entry_date).label('day'),
        func.sum(TimeEntry.time_minutes).label('minutes')
    ).filter(
        TimeEntry.entry_date >= seven_days_ago.date(),
        TimeEntry.sync_status == 'synced'
    ).group_by(func.date(TimeEntry.entry_date)).order_by('day').all()

    # Format as list of dicts for recharts
    chart_data = [
        {
            'day': row.day.strftime('%a'),  # Mon, Tue, etc.
            'minutes': float(row.minutes) or 0
        }
        for row in weekly_data
    ]

    # Fill missing days
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    filled_data = {d: 0 for d in days}
    for item in chart_data:
        filled_data[item['day']] = item['minutes']
    chart_data = [{'day': d, 'minutes': filled_data[d]} for d in days]

    return {
        'open_conflicts': open_conflicts,
        'last_sync': last_sync,
        'weekly_minutes': chart_data
    }

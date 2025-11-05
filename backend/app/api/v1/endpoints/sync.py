from typing import Annotated, Optional
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import logging
from fastapi import APIRouter, Depends, HTTPException, status
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

log = logging.getLogger(__name__)
router = APIRouter()

@router.post("/run", response_model=SyncResponse)
async def run_sync(
    request: SyncRequest = Depends(),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Trigger a manual sync run with optional date range."""
    # Resolve dates
    end_d = date.today().isoformat() if not request.end_date else request.end_date
    start_d = (date.today() - timedelta(days=30)).isoformat() if not request.start_date else request.start_date
    
    # Fetch active connectors
    zammad_conn = db.query(DBConnector).filter(DBConnector.type == "zammad", DBConnector.is_active == True).first()
    kimai_conn = db.query(DBConnector).filter(DBConnector.type == "kimai", DBConnector.is_active == True).first()
    
    if not zammad_conn or not kimai_conn:
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

    # Fetch active connectors
    zammad_conn = db.query(DBConnector).filter(DBConnector.type == "zammad", DBConnector.is_active == True).first()
    kimai_conn = db.query(DBConnector).filter(DBConnector.type == "kimai", DBConnector.is_active == True).first()
    
    if not zammad_conn or not kimai_conn:
        # Update SyncRun for no connectors
        sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
        sync_run.status = 'failed'
        sync_run.error_message = "No active Zammad and Kimai connectors configured"
        sync_run.entries_synced = 0
        sync_run.entries_failed = 1
        sync_run.conflicts_detected = 0
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active Zammad and Kimai connectors must be configured and active."
        )
    
    log.info(f"Sync request received for {start_d} to {end_d}, run_id: {sync_run_id}")
    
    # Decrypt tokens
    zammad_token = decrypt_data(zammad_conn.api_token)
    kimai_token = decrypt_data(kimai_conn.api_token)
    
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
        stats = await sync_service.sync_time_entries(start_d, end_d, trigger_type='manual')
        
        # Update SyncRun on success
        sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
        sync_run.status = 'completed'
        sync_run.entries_synced = stats["created"]
        sync_run.entries_failed = stats.get("unmapped", 0) + stats.get("ignored_unmapped", 0)
        sync_run.conflicts_detected = stats["conflicts"]
        db.commit()

        log.info(f"Sync completed successfully: processed={stats['processed']}, created={stats['created']}, skipped={stats['skipped']}, conflicts={stats['conflicts']}")
        return SyncResponse(
            status="success",
            message=f"Sync completed for {start_d} to {end_d}",
            start_date=start_d,
            end_date=end_d,
            num_processed=stats["processed"],
            num_created=stats["created"],
            num_skipped=stats["skipped"],
            num_conflicts=stats["conflicts"]
        )
    except ValueError as ve:
        log.error(f"ValueError during sync: {str(ve)}")
        log.error(f"Stack trace: {traceback.format_exc()}")
        
        # Update SyncRun on validation error
        sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
        sync_run.status = 'failed'
        sync_run.error_message = f"Validation error: {str(ve)}"
        sync_run.entries_synced = 0
        sync_run.entries_failed = 1
        sync_run.conflicts_detected = 0
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Sync validation error: {str(ve)}"
        )
    except Exception as e:
        log.error(f"Unexpected error during sync: {str(e)}")
        log.error(f"Stack trace: {traceback.format_exc()}")
        
        # Update SyncRun on unexpected error
        sync_run.end_time = datetime.now(ZoneInfo('Europe/Brussels'))
        sync_run.status = 'failed'
        sync_run.error_message = str(e)
        sync_run.entries_synced = 0
        sync_run.entries_failed = 1
        sync_run.conflicts_detected = 0
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Sync failed: {str(e)}"
        )

@router.get("/runs", response_model=list[dict])
async def get_sync_runs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve history of sync runs."""
    sync_runs = db.query(SyncRun).order_by(SyncRun.start_time.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": sr.id,
            "trigger_type": sr.trigger_type,
            "started_at": sr.start_time.isoformat() if sr.start_time else None,
            "ended_at": sr.end_time.isoformat() if sr.end_time else None,
            "status": sr.status,
            "entries_fetched": sr.entries_fetched,
            "entries_synced": sr.entries_synced,
            "entries_failed": sr.entries_failed,
            "conflicts_detected": sr.conflicts_detected,
            "error_message": sr.error_message
        }
        for sr in sync_runs
    ]

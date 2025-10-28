from typing import Annotated, Optional
from datetime import date, timedelta
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
        log.info(f"Starting sync process for period {start_d} to {end_d}")
        stats = await sync_service.sync_time_entries(start_d, end_d)
        log.info(f"Sync completed successfully: processed={stats['processed']}, created={stats['created']}, conflicts={stats['conflicts']}")
        return SyncResponse(
            status="success",
            message=f"Sync completed for {start_d} to {end_d}",
            start_date=start_d,
            end_date=end_d,
            num_processed=stats["processed"],
            num_created=stats["created"],
            num_conflicts=stats["conflicts"]
        )
    except ValueError as ve:
        log.error(f"ValueError during sync: {str(ve)}")
        log.error(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Sync validation error: {str(ve)}"
        )
    except Exception as e:
        log.error(f"Unexpected error during sync: {str(e)}")
        log.error(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Sync failed: {str(e)}"
        )

@router.get("/runs", response_model=list[dict])  # Assuming SyncRun model for future
async def get_sync_runs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve history of sync runs (placeholder for SyncRun model implementation)."""
    # TODO: Implement when SyncRun model and logging in SyncService added
    return []

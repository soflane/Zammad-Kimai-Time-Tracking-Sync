"""APScheduler integration for periodic sync jobs."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connector import Connector
from app.models.sync_run import SyncRun
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.services.sync_service import SyncService
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService
from app.utils.encrypt import decrypt_data

log = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Concurrency management
_sync_running = False  # Guard for 'skip' mode
_sync_queue = []  # Queue for 'queue' mode


async def scheduled_sync_job():
    """Execute scheduled sync with concurrency handling."""
    global _sync_running, _sync_queue
    
    from app.models.schedule import Schedule
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get schedule config
        schedule = db.query(Schedule).first()
        if not schedule or not schedule.enabled:
            log.info("Scheduled sync skipped: scheduler disabled")
            return
        
        # Concurrency handling
        if schedule.concurrency == 'skip':
            if _sync_running:
                log.warning("Scheduled sync skipped: previous run still active")
                return
        elif schedule.concurrency == 'queue':
            if _sync_running:
                if len(_sync_queue) < 5:  # Prevent unbounded queue
                    _sync_queue.append(datetime.now())
                    log.info(f"Scheduled sync queued (queue size: {len(_sync_queue)})")
                else:
                    log.warning("Scheduled sync queue full, skipping")
                return
        
        _sync_running = True
        log.info("Starting scheduled sync job")
        
        # Fetch connectors
        zammad_conn = db.query(Connector).filter(
            Connector.type == "zammad", 
            Connector.is_active == True
        ).first()
        kimai_conn = db.query(Connector).filter(
            Connector.type == "kimai", 
            Connector.is_active == True
        ).first()
        
        if not zammad_conn or not kimai_conn:
            log.error("Scheduled sync failed: connectors not configured")
            _sync_running = False
            return
        
        # Decrypt tokens
        zammad_token = decrypt_data(zammad_conn.api_token)
        kimai_token = decrypt_data(kimai_conn.api_token)
        
        # Create sync run
        sync_run = SyncRun(
            trigger_type='scheduled',
            start_time=datetime.now(ZoneInfo('Europe/Brussels')),
            status='running'
        )
        db.add(sync_run)
        db.commit()
        
        log.info(f"Starting scheduled sync run #{sync_run.id}")
        
        # Instantiate connectors
        zammad_config = {
            "base_url": str(zammad_conn.base_url),
            "api_token": zammad_token,
            "settings": zammad_conn.settings or {}
        }
        kimai_config = {
            "base_url": str(kimai_conn.base_url),
            "api_token": kimai_token,
            "settings": kimai_conn.settings or {}
        }
        
        zammad_instance = ZammadConnector(zammad_config)
        kimai_instance = KimaiConnector(kimai_config)
        
        # Create sync service
        sync_service = SyncService(
            zammad_connector=zammad_instance,
            kimai_connector=kimai_instance,
            normalizer_service=NormalizerService(),
            reconciliation_service=ReconciliationService(),
            db=db
        )
        
        # Sync last 30 days
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        stats = await sync_service.sync_time_entries(
            thirty_days_ago.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d"),
            sync_run,
            trigger_type='scheduled'
        )
        
        log.info(f"Scheduled sync #{sync_run.id} completed: {stats}")
        
        # Handle notifications if enabled
        if schedule.notifications:
            conflicts = stats.get('conflicts', 0)
            failed = stats.get('failed', 0)
            
            # Trigger notification if conflicts > 10 or any failures
            if conflicts > 10 or failed > 0:
                log.warning(
                    f"Notification threshold reached: conflicts={conflicts}, failed={failed}"
                )
                # TODO: Implement email/webhook notification
                # For now, just log it - can be extended with SMTP or webhook calls
        
    except Exception as e:
        log.error(f"Scheduled sync failed: {e}", exc_info=True)
    finally:
        _sync_running = False
        db.close()
        
        # Process queue if applicable
        if _sync_queue:
            _sync_queue.pop(0)
            log.info("Processing queued sync job")
            await scheduled_sync_job()


def reschedule_sync_job(cron: str, enabled: bool):
    """Dynamically reschedule the sync job without restarting the app."""
    job_id = "periodic_sync_job"
    
    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        log.info(f"Removed existing job: {job_id}")
    
    # Add new job if enabled
    if enabled:
        try:
            trigger = CronTrigger.from_crontab(cron)
            scheduler.add_job(
                scheduled_sync_job,
                trigger=trigger,
                id=job_id,
                replace_existing=True
            )
            log.info(f"Scheduled sync job updated: cron='{cron}'")
        except Exception as e:
            log.error(f"Failed to schedule job with cron '{cron}': {e}")
            raise
    else:
        log.info("Scheduled sync job disabled")


def start_scheduler():
    """Start the APScheduler and load initial schedule."""
    from app.models.schedule import Schedule
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Load initial schedule from database
        schedule = db.query(Schedule).first()
        if schedule and schedule.enabled:
            reschedule_sync_job(schedule.cron, True)
            log.info(f"Loaded schedule from database: cron='{schedule.cron}'")
        else:
            log.info("No active schedule found in database")
    except Exception as e:
        log.warning(f"Failed to load initial schedule: {e}")
    finally:
        db.close()
    
    # Start scheduler if not already running
    if not scheduler.running:
        scheduler.start()
        log.info("APScheduler started successfully")


def shutdown_scheduler():
    """Shutdown the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        log.info("APScheduler shut down successfully")

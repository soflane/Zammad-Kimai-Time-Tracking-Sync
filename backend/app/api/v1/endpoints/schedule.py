"""Schedule endpoints for periodic sync configuration."""

from typing import Annotated
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from croniter import croniter

from app.database import get_db
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleResponse, ScheduleUpdate
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.utils.audit_logger import create_audit_log

log = logging.getLogger(__name__)
router = APIRouter()


def compute_next_runs(cron: str, timezone: str, count: int = 3) -> list[str]:
    """Compute next N run times from cron expression."""
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        iter_obj = croniter(cron, now)
        return [iter_obj.get_next(datetime).isoformat() for _ in range(count)]
    except Exception as e:
        log.warning(f"Failed to compute next runs: {e}")
        return []


@router.get("/", response_model=ScheduleResponse)
async def get_schedule(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Get current schedule configuration."""
    schedule = db.query(Schedule).first()
    
    if not schedule:
        # Create default schedule if none exists
        schedule = Schedule(
            cron="0 */6 * * *",  # Every 6 hours
            timezone="UTC",
            concurrency="skip",
            notifications=False,
            enabled=False
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        log.info("Created default schedule configuration")
    
    # Compute next runs if enabled
    next_runs = compute_next_runs(schedule.cron, schedule.timezone) if schedule.enabled else []
    
    return ScheduleResponse(
        id=schedule.id,
        cron=schedule.cron,
        timezone=schedule.timezone,
        concurrency=schedule.concurrency,
        notifications=schedule.notifications,
        enabled=schedule.enabled,
        next_runs=next_runs,
        updated_at=schedule.updated_at.isoformat(),
        created_at=schedule.created_at.isoformat()
    )


@router.put("/", response_model=ScheduleResponse)
async def update_schedule(
    http_request: Request,
    update: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Update schedule configuration and reschedule job."""
    schedule = db.query(Schedule).first()
    
    if not schedule:
        raise HTTPException(
            status_code=404, 
            detail="Schedule not found. Use GET /api/v1/schedule first to initialize."
        )
    
    # Track changes for audit
    changes = {}
    
    # Apply updates
    if update.cron is not None:
        changes['cron'] = {'old': schedule.cron, 'new': update.cron}
        schedule.cron = update.cron
    
    if update.timezone is not None:
        changes['timezone'] = {'old': schedule.timezone, 'new': update.timezone}
        schedule.timezone = update.timezone
    
    if update.concurrency is not None:
        changes['concurrency'] = {'old': schedule.concurrency, 'new': update.concurrency}
        schedule.concurrency = update.concurrency
    
    if update.notifications is not None:
        changes['notifications'] = {'old': schedule.notifications, 'new': update.notifications}
        schedule.notifications = update.notifications
    
    if update.enabled is not None:
        changes['enabled'] = {'old': schedule.enabled, 'new': update.enabled}
        schedule.enabled = update.enabled
    
    db.commit()
    db.refresh(schedule)
    
    # Reschedule the job dynamically (import here to avoid circular dependency)
    try:
        from app.scheduler import reschedule_sync_job
        reschedule_sync_job(schedule.cron, schedule.enabled)
        log.info(f"Schedule updated and rescheduled: cron='{schedule.cron}', enabled={schedule.enabled}")
    except Exception as e:
        log.error(f"Failed to reschedule sync job: {e}")
        # Don't fail the request - schedule was saved to DB
    
    # Audit log
    create_audit_log(
        db=db,
        request=http_request,
        action="schedule_updated",
        user=current_user.username if current_user else None,
        details={'changes': changes}
    )
    
    # Compute next runs
    next_runs = compute_next_runs(schedule.cron, schedule.timezone) if schedule.enabled else []
    
    return ScheduleResponse(
        id=schedule.id,
        cron=schedule.cron,
        timezone=schedule.timezone,
        concurrency=schedule.concurrency,
        notifications=schedule.notifications,
        enabled=schedule.enabled,
        next_runs=next_runs,
        updated_at=schedule.updated_at.isoformat(),
        created_at=schedule.created_at.isoformat()
    )

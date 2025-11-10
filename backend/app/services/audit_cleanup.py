"""Audit log cleanup service for managing retention policies."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.audit_log import AuditLog

log = logging.getLogger(__name__)


def cleanup_old_access_logs(db: Session, days_to_keep: int = 90) -> int:
    """
    Delete access logs (login/API access) older than specified days.
    Sync logs (action starts with 'sync_') are never deleted.
    
    Args:
        db: Database session
        days_to_keep: Number of days to retain access logs (default: 90)
        
    Returns:
        Number of audit log entries deleted
        
    Usage:
        from app.services.audit_cleanup import cleanup_old_access_logs
        
        # Manual cleanup
        deleted_count = cleanup_old_access_logs(db, days_to_keep=90)
        
        # Scheduled cleanup (add to APScheduler)
        scheduler.add_job(
            lambda: cleanup_old_access_logs(get_db_session()),
            IntervalTrigger(days=1),
            id="audit_cleanup_job"
        )
    """
    cutoff_date = datetime.now(ZoneInfo('Europe/Brussels')) - timedelta(days=days_to_keep)
    
    # Define access log actions (everything except sync-related)
    # Sync logs have actions like: sync_triggered, sync_completed, sync_failed
    # Access logs have actions like: login_success, login_failed, connector_created, etc.
    
    # Delete old access logs (NOT starting with 'sync')
    deleted = db.query(AuditLog).filter(
        and_(
            AuditLog.created_at < cutoff_date,
            ~AuditLog.action.like('sync%')  # Keep all sync-related logs
        )
    ).delete(synchronize_session=False)
    
    db.commit()
    
    log.info(f"Audit cleanup: Deleted {deleted} access log entries older than {days_to_keep} days (cutoff: {cutoff_date.isoformat()})")
    
    return deleted


def get_audit_log_stats(db: Session) -> dict:
    """
    Get statistics about audit log storage.
    
    Returns:
        Dictionary with counts of different log types and oldest entries
    """
    total_logs = db.query(AuditLog).count()
    
    # Count by log type
    access_logs = db.query(AuditLog).filter(~AuditLog.action.like('sync%')).count()
    sync_logs = db.query(AuditLog).filter(AuditLog.action.like('sync%')).count()
    
    # Oldest entries
    oldest_access = db.query(AuditLog).filter(
        ~AuditLog.action.like('sync%')
    ).order_by(AuditLog.created_at.asc()).first()
    
    oldest_sync = db.query(AuditLog).filter(
        AuditLog.action.like('sync%')
    ).order_by(AuditLog.created_at.asc()).first()
    
    return {
        "total_logs": total_logs,
        "access_logs": access_logs,
        "sync_logs": sync_logs,
        "oldest_access_log": oldest_access.created_at.isoformat() if oldest_access else None,
        "oldest_sync_log": oldest_sync.created_at.isoformat() if oldest_sync else None
    }

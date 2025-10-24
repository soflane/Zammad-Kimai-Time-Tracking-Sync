from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from hmac import compare_digest
from hashlib import sha1
import base64

from app.database import get_db
from app.services.sync_service import SyncService
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.services.normalizer import NormalizerService
from app.services.reconciler import ReconciliationService
from app.models.connector import Connector as DBConnector
from app.utils.encrypt import decrypt_data
from app.models.audit_log import AuditLog
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.config import settings  # Assume webhook_secret in config

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"]
)

@router.post("/zammad", status_code=status.HTTP_200_OK)
async def zammad_webhook(
    request: Request,
    x_zammad_signature: str = Header(..., alias="X-Zammad-Signature"),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None  # Optional for webhook
):
    """Receive and process Zammad webhook for real-time sync."""
    # Verify HMAC signature
    expected_signature = "sha1=" + base64.b64encode(
        sha1((settings.webhook_secret + await request.body()).encode()).hexdigest().encode()
    ).decode()
    if not compare_digest(x_zammad_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    
    # Parse body for ticket_id (Zammad webhook JSON includes ticket.id)
    body = await request.json()
    ticket_id = body.get("ticket", {}).get("id")
    if not ticket_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing ticket ID")
    
    # Fetch active connectors
    zammad_conn = db.query(DBConnector).filter(DBConnector.type == "zammad", DBConnector.is_active == True).first()
    kimai_conn = db.query(DBConnector).filter(DBConnector.type == "kimai", DBConnector.is_active == True).first()
    if not zammad_conn or not kimai_conn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connectors not configured")
    
    # Decrypt tokens
    zammad_token = decrypt_data(zammad_conn.api_token)
    kimai_token = decrypt_data(kimai_conn.api_token)
    
    # Instantiate
    zammad_instance = ZammadConnector({"base_url": str(zammad_conn.base_url), "api_token": zammad_token})
    kimai_instance = KimaiConnector({"base_url": str(kimai_conn.base_url), "api_token": kimai_token})
    normalizer = NormalizerService()
    reconciler = ReconciliationService()
    
    sync_service = SyncService(
        zammad_connector=zammad_instance,
        kimai_connector=kimai_instance,
        normalizer_service=normalizer,
        reconciliation_service=reconciler,
        db=db
    )
    
    # Trigger sync for last day to catch recent changes (or enhance for single ticket; V1 uses full range)
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    try:
        stats = await sync_service.sync_time_entries(start_date, end_date)
        # Log webhook receipt
        audit_log = AuditLog(
            action="webhook_received",
            entity_type="zammad_ticket",
            entity_id=ticket_id,
            user="webhook",
            details={"period": f"{start_date} to {end_date}", "stats": stats, "body_summary": {"ticket_id": ticket_id}}
        )
        db.add(audit_log)
        db.commit()
        return {"status": "processed", "ticket_id": ticket_id, "stats": stats}
    except Exception as e:
        audit_log = AuditLog(
            action="webhook_error",
            entity_type="zammad_ticket",
            entity_id=ticket_id,
            user="webhook",
            details={"error": str(e), "body_summary": {"ticket_id": ticket_id}}
        )
        db.add(audit_log)
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")

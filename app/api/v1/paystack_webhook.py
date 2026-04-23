import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.paystack_service import PaystackService

# Reuse existing webhook logic without changing behavior.
from app.api.v1.payments import handle_paystack_payment_webhook
from app.api.v1.admin_payouts import handle_paystack_transfer_webhook


router = APIRouter(tags=["Paystack"])
paystack_service = PaystackService()
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Unified Paystack webhook endpoint.

    Paystack allows only one webhook URL; we dispatch internally by event name.
    - transfer.* events -> payout transfer handler
    - everything else    -> payments handler (currently processes charge.success)
    """
    raw_body = await request.body()

    if not paystack_service.verify_webhook_signature(raw_body, x_paystack_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()
    print("\n\n\n\n\n",event, "\n\n\n\n")
    event_name = str(event.get("event") or "")

    if event_name.startswith("transfer."):
        return handle_paystack_transfer_webhook(event=event, db=db)

    return handle_paystack_payment_webhook(event=event, db=db)


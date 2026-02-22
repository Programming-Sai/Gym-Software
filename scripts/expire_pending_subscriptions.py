# scripts/expire_pending_subscriptions.py
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models import Subscription, Payment
from app.core.config import settings

THRESH = settings.SUBSCRIPTION_PENDING_THRESHOLD_HOURS or 24

def run():
    cutoff = datetime.utcnow() - timedelta(hours=THRESH)
    db = SessionLocal()
    try:
        pending = db.query(Subscription).filter(
            Subscription.status == "pending",
            Subscription.created_at < cutoff
        ).all()
        for s in pending:
            # mark subscription cancelled so unique index frees up
            s.status = "cancelled"
            # mark associated payments as failed
            for p in (s.payments or []):
                if p.status == "pending":
                    p.status = "failed"
                    # append metadata
                    pm = p.payment_metadata or {}
                    pm["auto_expired"] = {"expired_at": datetime.utcnow().isoformat()}
                    p.payment_metadata = pm
            db.add(s)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    run()
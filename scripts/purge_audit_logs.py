import argparse
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.audit_logs import AuditLog


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge audit logs older than N days.")
    parser.add_argument("--keep-days", type=int, default=30, help="Keep only the most recent N days")
    parser.add_argument("--dry-run", action="store_true", help="Show how many rows would be deleted")
    args = parser.parse_args()

    cutoff = datetime.utcnow() - timedelta(days=int(args.keep_days))

    db = SessionLocal()
    try:
        q = db.query(AuditLog).filter(AuditLog.created_at < cutoff)
        if args.dry_run:
            count = q.count()
            print(f"[dry-run] would delete {count} audit_logs rows older than {args.keep_days} days (cutoff={cutoff.isoformat()}Z)")
            return 0

        deleted = q.delete(synchronize_session=False)
        db.commit()
        print(f"deleted {deleted} audit_logs rows older than {args.keep_days} days (cutoff={cutoff.isoformat()}Z)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())


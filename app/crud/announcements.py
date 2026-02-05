from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models.announcements import Announcement, AnnouncementRead


def create_announcement(db: Session, announcement: Announcement):
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


def list_published_announcements_for_gym(
    db: Session,
    *,
    gym_id: str,
    user_id: str
):
    now = datetime.utcnow()

    results = (
        db.query(   
            Announcement,
            AnnouncementRead.read_id.label("read_id")
        )
        .outerjoin(
            AnnouncementRead,
            and_(
                AnnouncementRead.announcement_id == Announcement.announcement_id,
                AnnouncementRead.user_id == user_id
            )
        )
        .filter(
            Announcement.gym_id == gym_id,
            Announcement.status == "published",
            Announcement.expires_at.is_(None) | (Announcement.expires_at > now),
        )
        .order_by(Announcement.created_at.desc())
        .all()
    )

    return results


def mark_announcement_as_read(
    db: Session,
    *,
    announcement_id: str,
    user_id: str
):
    exists = (
        db.query(AnnouncementRead)
        .filter(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == user_id
        )
        .first()
    )

    if exists:
        return exists

    read = AnnouncementRead(
        announcement_id=announcement_id,
        user_id=user_id
    )
    db.add(read)
    db.commit()
    return read

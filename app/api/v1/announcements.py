from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.dependencies import get_db, get_current_user
from app.models.announcements import Announcement
from app.models.gyms import Gym

router = APIRouter(tags=["Announcements"])


@router.post("/{announcement_id}/publish")
def publish_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    announcement = db.query(Announcement).filter(
        Announcement.announcement_id == announcement_id
    ).first()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if announcement.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft announcements can be published"
        )

    # Permission checks
    if announcement.target_type == "platform":
        if not user.role == "gym_owner":
            raise HTTPException(status_code=403, detail="Admins only")
    else:
        gym = db.query(Gym).filter(Gym.gym_id == announcement.gym_id).first()
        if not gym:
            raise HTTPException(status_code=404, detail="Gym not found")

        if not (user.role == "gym_owner" or user.user_id in {announcement.created_by, gym.owner_id}):
            raise HTTPException(status_code=403, detail="Permission denied")

    # Publish
    announcement.status = "published"
    if not announcement.publish_at:
        announcement.publish_at = datetime.utcnow()

    db.commit()
    return {"status": "published"}

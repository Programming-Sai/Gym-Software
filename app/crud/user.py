

from app.models.users import User
from sqlalchemy.orm import Session


def mark_email_verified(db: Session, user_id: str):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.email_verified = True
        db.commit()
        db.refresh(user)
        return user
    return None

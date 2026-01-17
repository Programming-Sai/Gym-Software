

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

def get_user_by_email(db, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db, user_id: str):
    return db.query(User).filter(User.user_id == user_id).first()

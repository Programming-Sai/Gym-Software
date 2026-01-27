from sqlalchemy.orm import Session
from app.models.relationships import UserFavoriteGym


def toggle_favorite_gym(db: Session, user_id: str, gym_id: str):
    fav = db.query(UserFavoriteGym).filter(
        UserFavoriteGym.user_id == user_id,
        UserFavoriteGym.gym_id == gym_id
    ).first()

    if fav:
        db.delete(fav)
        return False

    fav = UserFavoriteGym(user_id=user_id, gym_id=gym_id)
    db.add(fav)
    return True


def get_user_favorites(db: Session, user_id: str):
    return db.query(UserFavoriteGym).filter(
        UserFavoriteGym.user_id == user_id
    ).all()

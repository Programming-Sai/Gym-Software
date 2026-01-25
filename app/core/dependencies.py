from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.jwt import decode_token
from app.models.auth import Session as DBSession
from app.models.users import User
from app.models.gyms import Gym



security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    session = db.query(DBSession).filter(
        DBSession.access_token == token,
        DBSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.query(User).filter(User.user_id == user_id).first()

    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="Access denied")

    return user


def require_gym_owner(gym_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    if gym.owner_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this gym")
    return user

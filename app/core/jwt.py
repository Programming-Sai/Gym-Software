from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(subject: str):
    payload = {
        "sub": subject,
        "exp": datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[ALGORITHM]
    )

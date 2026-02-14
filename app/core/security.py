# core/security.py
from fastapi import HTTPException
from passlib.context import CryptContext
import hashlib
import secrets
from urllib.parse import urlparse
from app.core.config import settings




_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password = hashlib.sha256(password_bytes).hexdigest()
    return _pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)

def create_refresh_token():
    return secrets.token_urlsafe(64)



def validate_callback(url: str) -> None:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    allowed = settings.ALLOWED_CALLBACK_DOMAINS

    # allow all
    if "*" in allowed:
        return

    if base not in allowed:
        raise HTTPException(status_code=400, detail="Invalid callback URL")

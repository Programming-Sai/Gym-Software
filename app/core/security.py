# core/security.py
from passlib.context import CryptContext
import hashlib


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password = hashlib.sha256(password_bytes).hexdigest()
    return _pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)

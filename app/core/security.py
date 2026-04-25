from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expires_delta
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token({"sub": subject, "type": "access"}, expires_delta)


def create_refresh_token(subject: str) -> str:
    expires_delta = timedelta(minutes=settings.refresh_token_expire_minutes)
    return _create_token({"sub": subject, "type": "refresh"}, expires_delta)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def safe_decode_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_token(token)
    except JWTError:
        return None


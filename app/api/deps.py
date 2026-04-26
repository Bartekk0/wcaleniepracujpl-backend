from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import safe_decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.user_service import get_user_by_email

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = safe_decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    user = get_user_by_email(db, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )
    if not user.is_activated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )
    return user


def require_roles(*allowed_roles: UserRole):
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return current_user

    return role_dependency


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    return require_roles(UserRole.ADMIN)(current_user)


def require_recruiter(current_user: User = Depends(get_current_user)) -> User:
    return require_roles(UserRole.RECRUITER)(current_user)


def require_candidate(current_user: User = Depends(get_current_user)) -> User:
    return require_roles(UserRole.CANDIDATE)(current_user)

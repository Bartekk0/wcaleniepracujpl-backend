from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str | None = None,
    role: UserRole = UserRole.CANDIDATE,
) -> User:
    normalized_email = email.strip().lower()
    user = User(
        email=normalized_email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        return False

    db.delete(user)
    db.commit()
    return True

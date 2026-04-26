from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import verify_password
from app.db import models_registry  # noqa: F401
from app.db.base import Base
from app.models.user import UserRole
from app.services.user_service import create_user, delete_user, get_user_by_email


def _build_test_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_factory()


def test_create_user_hashes_password_and_persists_user() -> None:
    db = _build_test_session()
    try:
        user = create_user(
            db=db,
            email="Test@Example.COM",
            password="StrongPass123!",
            full_name="Test User",
            role=UserRole.RECRUITER,
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.RECRUITER
        assert user.hashed_password != "StrongPass123!"
        assert verify_password("StrongPass123!", user.hashed_password) is True
    finally:
        db.close()


def test_get_user_by_email_returns_matching_user() -> None:
    db = _build_test_session()
    try:
        created_user = create_user(
            db=db,
            email="hello@example.com",
            password="StrongPass123!",
        )

        found_user = get_user_by_email(db, "HELLO@EXAMPLE.COM")
        missing_user = get_user_by_email(db, "missing@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert missing_user is None
    finally:
        db.close()


def test_delete_user_removes_existing_user() -> None:
    db = _build_test_session()
    try:
        created_user = create_user(
            db=db,
            email="delete-me@example.com",
            password="StrongPass123!",
        )

        deleted = delete_user(db, created_user.id)
        found_user = get_user_by_email(db, "delete-me@example.com")

        assert deleted is True
        assert found_user is None
    finally:
        db.close()


def test_delete_user_returns_false_for_missing_user() -> None:
    db = _build_test_session()
    try:
        assert delete_user(db, 999999) is False
    finally:
        db.close()

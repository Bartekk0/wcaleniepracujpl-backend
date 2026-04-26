import pytest
from fastapi import HTTPException

from app.api.deps import require_admin, require_candidate, require_recruiter
from app.models.user import User, UserRole


def _build_user(role: UserRole) -> User:
    return User(
        email=f"{role.value}@example.com",
        hashed_password="hashed",
        role=role,
        is_activated=True,
    )


def test_require_admin_allows_admin() -> None:
    user = _build_user(UserRole.ADMIN)

    result = require_admin(user)

    assert result.role == UserRole.ADMIN


def test_require_admin_blocks_non_admin() -> None:
    user = _build_user(UserRole.CANDIDATE)

    with pytest.raises(HTTPException) as exc:
        require_admin(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient permissions."


def test_require_recruiter_allows_recruiter() -> None:
    user = _build_user(UserRole.RECRUITER)

    result = require_recruiter(user)

    assert result.role == UserRole.RECRUITER


def test_require_candidate_allows_candidate() -> None:
    user = _build_user(UserRole.CANDIDATE)

    result = require_candidate(user)

    assert result.role == UserRole.CANDIDATE

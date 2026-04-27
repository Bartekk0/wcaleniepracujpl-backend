"""Tests for CV presign endpoint (router patched to avoid MinIO network I/O)."""

import importlib

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.services.user_service import create_user


def _create_user_and_login(
    client: TestClient,
    db_session: Session,
    *,
    email: str,
    role: UserRole,
) -> tuple[int, str]:
    user = create_user(
        db_session,
        email=email,
        password="StrongPass123!",
        full_name=f"{role.value.title()} User",
        role=role,
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    return user.id, login_response.json()["access_token"]


def test_candidate_cv_presign_returns_upload_metadata(monkeypatch, client: TestClient, db_session: Session) -> None:
    def _fake_presigned_upload_cv(*, candidate_user_id: int, filename: str) -> tuple[str, str, int]:
        return (
            f"cv/{candidate_user_id}/deadbeef_resume.pdf",
            "https://minio.example/presigned",
            3600,
        )

    applications_router_mod = importlib.import_module("app.domains.applications.router")
    monkeypatch.setattr(applications_router_mod, "presigned_upload_cv", _fake_presigned_upload_cv)

    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="cv.presign.candidate@example.com",
        role=UserRole.CANDIDATE,
    )

    response = client.post(
        "/api/v1/applications/cv-presign",
        json={"filename": "resume.pdf"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["upload_url"] == "https://minio.example/presigned"
    assert body["expires_in_seconds"] == 3600
    assert body["object_key"].startswith("cv/")
    assert body["object_key"].endswith("_resume.pdf")

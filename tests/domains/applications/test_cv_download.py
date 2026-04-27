"""Tests for CV presigned download endpoint (router patched to avoid MinIO network I/O)."""

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


def _approve_job(client: TestClient, db_session: Session, job_id: int) -> None:
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email=f"cvdl.admin.{job_id}.approve@example.com",
        role=UserRole.ADMIN,
    )
    approve_response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/approve",
        json={"note": "Approved for tests."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200


def _create_job_for_recruiter(
    client: TestClient,
    db_session: Session,
    recruiter_token: str,
    *,
    company_name: str,
    job_title: str,
) -> int:
    company_response = client.post(
        "/api/v1/companies",
        json={"name": company_name},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]
    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": job_title,
            "description": f"{job_title} description",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]
    _approve_job(client, db_session, job_id)
    return job_id


def test_candidate_cv_download_returns_download_url(
    monkeypatch,
    client: TestClient,
    db_session: Session,
) -> None:
    def _fake_presigned_download_cv(*, object_key: str) -> tuple[str, int]:
        return "https://minio.example/get-presigned", 3600

    monkeypatch.setattr(
        "app.domains.applications.service.presigned_download_cv",
        _fake_presigned_download_cv,
    )

    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    candidate_id, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        db_session,
        recruiter_token,
        company_name="CvDl Co",
        job_title="CvDl Job",
    )
    cv_key = f"cv/{candidate_id}/deadbeef_resume.pdf"
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Hi", "cv_object_key": cv_key},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = client.get(
        f"/api/v1/applications/{application_id}/cv-download",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["download_url"] == "https://minio.example/get-presigned"
    assert body["expires_in_seconds"] == 3600


def test_recruiter_cv_download_returns_download_url(
    monkeypatch,
    client: TestClient,
    db_session: Session,
) -> None:
    def _fake_presigned_download_cv(*, object_key: str) -> tuple[str, int]:
        return "https://minio.example/recruiter-get", 3600

    monkeypatch.setattr(
        "app.domains.applications.service.presigned_download_cv",
        _fake_presigned_download_cv,
    )

    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.recruiter2@example.com",
        role=UserRole.RECRUITER,
    )
    candidate_id, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate2@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        db_session,
        recruiter_token,
        company_name="CvDl Co 2",
        job_title="CvDl Job 2",
    )
    cv_key = f"cv/{candidate_id}/resume.pdf"
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cv_object_key": cv_key},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = client.get(
        f"/api/v1/applications/{application_id}/cv-download",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert response.status_code == 200
    assert response.json()["download_url"] == "https://minio.example/recruiter-get"


def test_candidate_cv_download_forbidden_for_other_candidates_application(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.recruiter3@example.com",
        role=UserRole.RECRUITER,
    )
    candidate_a_id, candidate_a_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate.a@example.com",
        role=UserRole.CANDIDATE,
    )
    _, candidate_b_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate.b@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        db_session,
        recruiter_token,
        company_name="CvDl Co 3",
        job_title="CvDl Job 3",
    )
    cv_key = f"cv/{candidate_a_id}/resume.pdf"
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cv_object_key": cv_key},
        headers={"Authorization": f"Bearer {candidate_a_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = client.get(
        f"/api/v1/applications/{application_id}/cv-download",
        headers={"Authorization": f"Bearer {candidate_b_token}"},
    )

    assert response.status_code == 403


def test_candidate_cv_download_forbidden_without_cv_still_returns_403_for_foreign_candidate(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.recruiter5@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_a_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate.5a@example.com",
        role=UserRole.CANDIDATE,
    )
    _, candidate_b_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate.5b@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        db_session,
        recruiter_token,
        company_name="CvDl Co 5",
        job_title="CvDl Job 5",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "No CV yet"},
        headers={"Authorization": f"Bearer {candidate_a_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = client.get(
        f"/api/v1/applications/{application_id}/cv-download",
        headers={"Authorization": f"Bearer {candidate_b_token}"},
    )

    assert response.status_code == 403


def test_cv_download_not_found_when_no_cv_uploaded(
    monkeypatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setattr(
        "app.domains.applications.service.presigned_download_cv",
        lambda **_: (_ for _ in ()).throw(AssertionError("should not presign")),
    )

    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.recruiter4@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="cvdl.candidate4@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        db_session,
        recruiter_token,
        company_name="CvDl Co 4",
        job_title="CvDl Job 4",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "No CV"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    response = client.get(
        f"/api/v1/applications/{application_id}/cv-download",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No CV uploaded for this application."

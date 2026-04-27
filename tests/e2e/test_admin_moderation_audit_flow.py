from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.job import Job
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


def test_admin_moderation_updates_job_state_and_writes_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_id, admin_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.admin@example.com",
        role=UserRole.ADMIN,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.recruiter@example.com",
        role=UserRole.RECRUITER,
    )

    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Moderation E2E Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Moderation E2E Job",
            "description": "Needs admin approval.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    approve_response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/approve",
        json={"note": "Approved in e2e flow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_response.status_code == 200
    payload = approve_response.json()
    assert payload["job"]["moderation_status"] == "approved"
    assert payload["audit_log"]["action"] == "job_approved"

    job = db_session.get(Job, job_id)
    assert job is not None
    assert job.moderation_status.value == "approved"
    assert job.moderated_by_admin_user_id == admin_id

    logs = list(
        db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.target_type == "job",
                AdminAuditLog.target_id == job_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].admin_user_id == admin_id
    assert logs[0].action == "job_approved"

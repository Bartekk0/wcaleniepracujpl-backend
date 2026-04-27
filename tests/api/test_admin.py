from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
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


def _create_job_for_recruiter(
    client: TestClient,
    token: str,
    *,
    company_name: str,
    job_title: str,
) -> int:
    company_response = client.post(
        "/api/v1/companies",
        json={"name": company_name},
        headers={"Authorization": f"Bearer {token}"},
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
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_response.status_code == 201
    return job_response.json()["id"]


def test_admin_can_list_moderation_queue_and_approve_job(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_id, admin_token = _create_user_and_login(
        client,
        db_session,
        email="admin.moderation@example.com",
        role=UserRole.ADMIN,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="admin.queue.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Moderation Queue Co",
        job_title="Moderation Queue Job",
    )

    queue_response = client.get(
        "/api/v1/admin/moderation/jobs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    approve_response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/approve",
        json={"note": "Looks good and compliant."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    queue_after_response = client.get(
        "/api/v1/admin/moderation/jobs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert queue_response.status_code == 200
    assert [item["id"] for item in queue_response.json()] == [job_id]
    assert approve_response.status_code == 200
    assert approve_response.json()["job"]["moderation_status"] == "approved"
    assert approve_response.json()["audit_log"]["admin_user_id"] == admin_id
    assert approve_response.json()["audit_log"]["action"] == "job_approved"
    assert queue_after_response.status_code == 200
    assert queue_after_response.json() == []

    audit_rows = list(db_session.execute(select(AdminAuditLog)).scalars().all())
    assert len(audit_rows) == 1
    assert audit_rows[0].target_type == "job"
    assert audit_rows[0].target_id == job_id
    assert audit_rows[0].action == "job_approved"


def test_admin_can_reject_job_and_repeat_moderation_is_blocked(
    client: TestClient,
    db_session: Session,
) -> None:
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email="admin.reject@example.com",
        role=UserRole.ADMIN,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="admin.reject.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Rejection Co",
        job_title="Rejected Job",
    )

    reject_response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/reject",
        json={"note": "Policy mismatch."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    second_moderation_response = client.post(
        f"/api/v1/admin/moderation/jobs/{job_id}/approve",
        json={"note": "Trying to flip state."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["job"]["moderation_status"] == "rejected"
    assert reject_response.json()["audit_log"]["action"] == "job_rejected"
    assert second_moderation_response.status_code == 409
    assert second_moderation_response.json()["detail"] == "Job is already moderated."


def test_admin_endpoints_enforce_admin_role_guard(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="admin.guard.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="admin.guard.candidate@example.com",
        role=UserRole.CANDIDATE,
    )

    recruiter_response = client.get(
        "/api/v1/admin/moderation/jobs",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    candidate_response = client.get(
        "/api/v1/admin/moderation/jobs",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert recruiter_response.status_code == 403
    assert candidate_response.status_code == 403
    assert recruiter_response.json()["detail"] == "Insufficient permissions."


def test_user_can_create_report_and_admin_can_resolve_with_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_id, admin_token = _create_user_and_login(
        client,
        db_session,
        email="admin.reports@example.com",
        role=UserRole.ADMIN,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="candidate.reports@example.com",
        role=UserRole.CANDIDATE,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="recruiter.report.target@example.com",
        role=UserRole.RECRUITER,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Reportable Co",
        job_title="Potentially Misleading Job",
    )

    create_response = client.post(
        f"/api/v1/admin/reports/jobs/{job_id}",
        json={"reason": "The posting details look suspicious."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["id"]
    assert create_response.json()["status"] == "open"

    resolve_response = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"note": "Reviewed and fixed."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["report"]["status"] == "resolved"
    assert resolve_response.json()["report"]["resolved_by_admin_user_id"] == admin_id
    assert resolve_response.json()["audit_log"]["action"] == "report_resolved"

    audit_rows = list(db_session.execute(select(AdminAuditLog)).scalars().all())
    assert any(
        row.target_type == "report"
        and row.target_id == report_id
        and row.action == "report_resolved"
        for row in audit_rows
    )


def test_admin_report_actions_enforce_role_and_handled_state(
    client: TestClient,
    db_session: Session,
) -> None:
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email="admin.report.guards@example.com",
        role=UserRole.ADMIN,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="candidate.report.guards@example.com",
        role=UserRole.CANDIDATE,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="recruiter.report.guards@example.com",
        role=UserRole.RECRUITER,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Report Guard Co",
        job_title="Guarded Report Job",
    )
    report_response = client.post(
        f"/api/v1/admin/reports/jobs/{job_id}",
        json={"reason": "Spam content in description."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]

    forbidden_response = client.post(
        f"/api/v1/admin/reports/{report_id}/dismiss",
        json={"note": "Should fail for candidate."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert forbidden_response.status_code == 403

    first_dismiss_response = client.post(
        f"/api/v1/admin/reports/{report_id}/dismiss",
        json={"note": "Reviewed and dismissed."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first_dismiss_response.status_code == 200
    assert first_dismiss_response.json()["report"]["status"] == "dismissed"

    second_dismiss_response = client.post(
        f"/api/v1/admin/reports/{report_id}/dismiss",
        json={"note": "Duplicate moderation."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second_dismiss_response.status_code == 409
    assert second_dismiss_response.json()["detail"] == "Report is already handled."

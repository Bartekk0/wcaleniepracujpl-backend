from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.report import Report, ReportStatus
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


def test_candidate_reports_job_admin_resolves_and_audit_log_recorded(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_id, admin_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.reports.admin@example.com",
        role=UserRole.ADMIN,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.reports.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.reports.recruiter@example.com",
        role=UserRole.RECRUITER,
    )

    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Reports E2E Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Reportable Job",
            "description": "Needs moderation attention.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    create_report_response = client.post(
        f"/api/v1/admin/reports/jobs/{job_id}",
        json={"reason": "Misleading salary range."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert create_report_response.status_code == 201
    report_id = create_report_response.json()["id"]
    assert create_report_response.json()["status"] == "open"

    list_response = client.get(
        "/api/v1/admin/reports",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    listed_ids = [row["id"] for row in list_response.json()]
    assert report_id in listed_ids

    resolve_response = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        json={"note": "Verified and corrected posting."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["report"]["status"] == "resolved"
    assert resolve_response.json()["audit_log"]["action"] == "report_resolved"

    row = db_session.get(Report, report_id)
    assert row is not None
    assert row.status in ("resolved", ReportStatus.RESOLVED)
    assert row.resolved_by_admin_user_id == admin_id

    logs = list(
        db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.target_type == "report",
                AdminAuditLog.target_id == report_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].admin_user_id == admin_id
    assert logs[0].action == "report_resolved"


def test_candidate_reports_job_admin_dismisses_and_audit_log_recorded(
    client: TestClient,
    db_session: Session,
) -> None:
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.dismiss.admin@example.com",
        role=UserRole.ADMIN,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.dismiss.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.dismiss.recruiter@example.com",
        role=UserRole.RECRUITER,
    )

    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Dismiss Reports Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Dismiss Target Job",
            "description": "Another listing.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    create_report_response = client.post(
        f"/api/v1/admin/reports/jobs/{job_id}",
        json={"reason": "Spam suspicion."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert create_report_response.status_code == 201
    report_id = create_report_response.json()["id"]

    dismiss_response = client.post(
        f"/api/v1/admin/reports/{report_id}/dismiss",
        json={"note": "No policy violation."},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["report"]["status"] == "dismissed"
    assert dismiss_response.json()["audit_log"]["action"] == "report_dismissed"

    row = db_session.get(Report, report_id)
    assert row is not None
    assert row.status in ("dismissed", ReportStatus.DISMISSED)

    logs = list(
        db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.target_type == "report",
                AdminAuditLog.target_id == report_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "report_dismissed"

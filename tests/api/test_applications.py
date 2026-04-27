from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def test_candidate_can_apply_and_list_own_applications(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    candidate_id, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Apps Co",
        job_title="Python Engineer",
    )

    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "I am a strong match."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    my_response = client.get(
        "/api/v1/applications/me",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert apply_response.status_code == 201
    assert apply_response.json()["job_id"] == job_id
    assert apply_response.json()["candidate_user_id"] == candidate_id
    assert apply_response.json()["status"] == "submitted"
    assert my_response.status_code == 200
    assert len(my_response.json()) == 1
    assert my_response.json()[0]["job_id"] == job_id


def test_recruiter_can_list_applications_for_owned_job(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.viewer@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="View Co",
        job_title="Data Engineer",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Please review my profile."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201

    recruiter_view_response = client.get(
        f"/api/v1/applications/jobs/{job_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert recruiter_view_response.status_code == 200
    payload = recruiter_view_response.json()
    assert len(payload) == 1
    assert payload[0]["job_id"] == job_id
    assert payload[0]["status"] == "submitted"


def test_application_endpoints_enforce_role_guards(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.guard.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.guard.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Guard Co",
        job_title="Guarded Job",
    )

    recruiter_apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    recruiter_me_response = client.get(
        "/api/v1/applications/me",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    candidate_recruiter_view_response = client.get(
        f"/api/v1/applications/jobs/{job_id}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert recruiter_apply_response.status_code == 403
    assert recruiter_me_response.status_code == 403
    assert candidate_recruiter_view_response.status_code == 403
    assert recruiter_apply_response.json()["detail"] == "Insufficient permissions."


def test_candidate_cannot_apply_twice_to_same_job(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.duplicate.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.duplicate.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Duplicate Co",
        job_title="Duplicate Guard Job",
    )

    first_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "First try"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    second_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Second try"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Application already exists for this job."


def test_recruiter_cannot_view_applications_for_unowned_job(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.owner.guard@example.com",
        role=UserRole.RECRUITER,
    )
    _, outsider_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.outsider.guard@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.guard.viewer@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        owner_recruiter_token,
        company_name="Owner Protected Co",
        job_title="Owner Protected Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Ownership visibility check"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201

    outsider_view = client.get(
        f"/api/v1/applications/jobs/{job_id}",
        headers={"Authorization": f"Bearer {outsider_recruiter_token}"},
    )

    assert outsider_view.status_code == 403
    assert outsider_view.json()["detail"] == "Recruiter has no access to this job."


def test_recruiter_can_transition_application_status_for_owned_job(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Status Flow Co",
        job_title="Status Flow Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Ready for review"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    reviewing_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    accepted_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert reviewing_response.status_code == 200
    assert reviewing_response.json()["status"] == "reviewing"
    assert accepted_response.status_code == 200
    assert accepted_response.json()["status"] == "accepted"


def test_application_status_forbids_invalid_transition(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.invalid.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.invalid.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Invalid Flow Co",
        job_title="Invalid Flow Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    invalid_transition_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert invalid_transition_response.status_code == 409
    assert (
        invalid_transition_response.json()["detail"]
        == "Invalid status transition: submitted -> accepted."
    )


def test_application_status_update_role_guards_and_access_control(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.guard.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, outsider_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.guard.outsider@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.guard.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.guard.admin@example.com",
        role=UserRole.ADMIN,
    )

    job_id = _create_job_for_recruiter(
        client,
        owner_recruiter_token,
        company_name="Guard Status Co",
        job_title="Guard Status Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    candidate_update_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    outsider_update_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {outsider_recruiter_token}"},
    )
    admin_update_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert candidate_update_response.status_code == 403
    assert candidate_update_response.json()["detail"] == "Insufficient permissions."
    assert outsider_update_response.status_code == 403
    assert outsider_update_response.json()["detail"] == "Recruiter has no access to this job."
    assert admin_update_response.status_code == 200
    assert admin_update_response.json()["status"] == "reviewing"


def test_status_change_creates_event_and_history_is_visible_to_candidate_and_recruiter(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="History Flow Co",
        job_title="History Flow Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    reviewing_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert reviewing_response.status_code == 200

    recruiter_history_response = client.get(
        f"/api/v1/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    candidate_history_response = client.get(
        f"/api/v1/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert recruiter_history_response.status_code == 200
    assert candidate_history_response.status_code == 200
    recruiter_history = recruiter_history_response.json()
    candidate_history = candidate_history_response.json()
    assert len(recruiter_history) == 1
    assert recruiter_history[0]["from_status"] == "submitted"
    assert recruiter_history[0]["to_status"] == "reviewing"
    assert candidate_history[0]["id"] == recruiter_history[0]["id"]


def test_application_history_endpoint_enforces_access_control(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, outsider_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.outsider@example.com",
        role=UserRole.RECRUITER,
    )
    _, owner_candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.owner.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    _, other_candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.other.candidate@example.com",
        role=UserRole.CANDIDATE,
    )

    job_id = _create_job_for_recruiter(
        client,
        owner_recruiter_token,
        company_name="History ACL Co",
        job_title="History ACL Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {owner_candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {owner_recruiter_token}"},
    )

    outsider_recruiter_history_response = client.get(
        f"/api/v1/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {outsider_recruiter_token}"},
    )
    other_candidate_history_response = client.get(
        f"/api/v1/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {other_candidate_token}"},
    )

    assert outsider_recruiter_history_response.status_code == 403
    assert (
        outsider_recruiter_history_response.json()["detail"]
        == "Recruiter has no access to this job."
    )
    assert other_candidate_history_response.status_code == 403
    assert (
        other_candidate_history_response.json()["detail"]
        == "Candidate has no access to this application."
    )


def test_admin_can_access_application_history(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.admin.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.admin.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    _, admin_token = _create_user_and_login(
        client,
        db_session,
        email="apps.history.admin@example.com",
        role=UserRole.ADMIN,
    )

    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="History Admin Co",
        job_title="History Admin Job",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    status_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert status_response.status_code == 200

    admin_history_response = client.get(
        f"/api/v1/applications/{application_id}/history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert admin_history_response.status_code == 200
    history = admin_history_response.json()
    assert len(history) == 1
    assert history[0]["from_status"] == "submitted"
    assert history[0]["to_status"] == "reviewing"


def test_application_status_update_returns_404_for_missing_application(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.missing-app.recruiter@example.com",
        role=UserRole.RECRUITER,
    )

    response = client.patch(
        "/api/v1/applications/999999/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found."


def test_application_status_update_returns_404_when_application_job_missing(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.missing-job.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="apps.status.missing-job.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    job_id = _create_job_for_recruiter(
        client,
        recruiter_token,
        company_name="Missing Job Co",
        job_title="Missing Job Status Flow",
    )
    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "Please review"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    job = db_session.get(Job, job_id)
    assert job is not None
    db_session.delete(job)
    db_session.commit()

    response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found."

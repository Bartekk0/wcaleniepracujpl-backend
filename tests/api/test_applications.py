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

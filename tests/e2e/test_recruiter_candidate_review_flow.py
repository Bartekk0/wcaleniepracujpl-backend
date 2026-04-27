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


def test_recruiter_publish_candidate_apply_recruiter_review_flow(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    candidate_id, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="e2e.candidate@example.com",
        role=UserRole.CANDIDATE,
    )

    company_response = client.post(
        "/api/v1/companies",
        json={"name": "E2E Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "E2E Backend Engineer",
            "description": "Work on end-to-end flow.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    apply_response = client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "cover_letter": "I am interested."},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]
    assert apply_response.json()["candidate_user_id"] == candidate_id
    assert apply_response.json()["status"] == "submitted"

    review_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewing"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "reviewing"

    accept_response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    candidate_view = client.get(
        "/api/v1/applications/me",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_view.status_code == 200
    assert len(candidate_view.json()) == 1
    assert candidate_view.json()[0]["id"] == application_id
    assert candidate_view.json()[0]["status"] == "accepted"

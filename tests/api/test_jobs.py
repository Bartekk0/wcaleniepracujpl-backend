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


def test_recruiter_can_create_job_for_owned_company(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.owner@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Backend Engineer",
            "location": "Remote",
            "employment_type": "full-time",
            "description": "Build and maintain APIs.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["company_id"] == company_id
    assert payload["title"] == "Backend Engineer"
    assert payload["location"] == "Remote"
    assert payload["employment_type"] == "full-time"


def test_job_create_requires_recruiter_role(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Only Recruiters Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    forbidden_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Forbidden Role",
            "description": "Should not be created by candidate.",
        },
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    unauthenticated_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "No Auth Role",
            "description": "Should not be created without token.",
        },
    )

    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == "Insufficient permissions."
    assert unauthenticated_response.status_code == 401


def test_recruiter_cannot_create_job_for_unrelated_company(
    client: TestClient,
    db_session: Session,
) -> None:
    _, owner_token = _create_user_and_login(
        client,
        db_session,
        email="company.owner@example.com",
        role=UserRole.RECRUITER,
    )
    _, other_recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="other.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Private Company"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Unauthorized Job",
            "description": "Should fail for non-member recruiter.",
        },
        headers={"Authorization": f"Bearer {other_recruiter_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Recruiter has no access to this company."


def test_public_and_candidate_can_list_and_read_job_details(
    client: TestClient,
    db_session: Session,
) -> None:
    _, recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.publisher@example.com",
        role=UserRole.RECRUITER,
    )
    _, candidate_token = _create_user_and_login(
        client,
        db_session,
        email="jobs.viewer@example.com",
        role=UserRole.CANDIDATE,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Public Jobs Co"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    create_job_response = client.post(
        "/api/v1/jobs",
        json={
            "company_id": company_id,
            "title": "Public Backend Engineer",
            "description": "Visible to everyone.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert create_job_response.status_code == 201
    job_id = create_job_response.json()["id"]

    public_list_response = client.get("/api/v1/jobs")
    candidate_list_response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    public_detail_response = client.get(f"/api/v1/jobs/{job_id}")

    assert public_list_response.status_code == 200
    assert len(public_list_response.json()) == 1
    assert public_list_response.json()[0]["title"] == "Public Backend Engineer"
    assert candidate_list_response.status_code == 200
    assert len(candidate_list_response.json()) == 1
    assert candidate_list_response.json()[0]["id"] == job_id
    assert public_detail_response.status_code == 200
    assert public_detail_response.json()["id"] == job_id


def test_job_detail_returns_404_for_missing_job(client: TestClient) -> None:
    response = client.get("/api/v1/jobs/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found."

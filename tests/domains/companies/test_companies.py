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
) -> str:
    create_user(
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
    return login_response.json()["access_token"]


def test_create_company_sets_owner_from_current_recruiter(
    client: TestClient,
    db_session: Session,
) -> None:
    recruiter_token = _create_user_and_login(
        client,
        db_session,
        email="recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    response = client.post(
        "/api/v1/companies",
        json={
            "name": "Acme Corp",
            "website_url": "https://acme.example",
            "location": "Warsaw",
            "description": "Hiring backend engineers.",
        },
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["name"] == "Acme Corp"
    assert payload["owner_user_id"] > 0
    assert payload["website_url"] == "https://acme.example"
    assert payload["location"] == "Warsaw"


def test_companies_endpoints_require_recruiter_role(
    client: TestClient,
    db_session: Session,
) -> None:
    candidate_token = _create_user_and_login(
        client,
        db_session,
        email="candidate@example.com",
        role=UserRole.CANDIDATE,
    )
    create_response = client.post(
        "/api/v1/companies",
        json={"name": "Forbidden Co"},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    list_response = client.get(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert create_response.status_code == 403
    assert list_response.status_code == 403
    assert create_response.json()["detail"] == "Insufficient permissions."
    assert list_response.json()["detail"] == "Insufficient permissions."


def test_list_companies_returns_only_current_recruiter_companies(
    client: TestClient,
    db_session: Session,
) -> None:
    recruiter_one_token = _create_user_and_login(
        client,
        db_session,
        email="recruiter.one@example.com",
        role=UserRole.RECRUITER,
    )
    recruiter_two_token = _create_user_and_login(
        client,
        db_session,
        email="recruiter.two@example.com",
        role=UserRole.RECRUITER,
    )

    create_first = client.post(
        "/api/v1/companies",
        json={"name": "Recruiter One Co"},
        headers={"Authorization": f"Bearer {recruiter_one_token}"},
    )
    create_second = client.post(
        "/api/v1/companies",
        json={"name": "Recruiter Two Co"},
        headers={"Authorization": f"Bearer {recruiter_two_token}"},
    )
    assert create_first.status_code == 201
    assert create_second.status_code == 201

    response = client.get(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {recruiter_one_token}"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert len(payload) == 1
    assert payload[0]["name"] == "Recruiter One Co"


def test_owner_can_add_recruiter_member_and_member_can_list_company(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_token = _create_user_and_login(
        client,
        db_session,
        email="owner@example.com",
        role=UserRole.RECRUITER,
    )
    member_email = "member@example.com"
    member_user = create_user(
        db_session,
        email=member_email,
        password="StrongPass123!",
        full_name="Member Recruiter",
        role=UserRole.RECRUITER,
    )
    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": member_email, "password": "StrongPass123!"},
    )
    assert member_login.status_code == 200
    member_token = member_login.json()["access_token"]

    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Team Company"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    add_member_response = client.post(
        f"/api/v1/companies/{company_id}/recruiters",
        json={"recruiter_user_id": member_user.id},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert add_member_response.status_code == 201
    assert add_member_response.json()["company_id"] == company_id

    member_companies = client.get(
        "/api/v1/companies",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert member_companies.status_code == 200
    payload = member_companies.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Team Company"


def test_only_owner_can_add_recruiter_member(
    client: TestClient,
    db_session: Session,
) -> None:
    owner_token = _create_user_and_login(
        client,
        db_session,
        email="owner2@example.com",
        role=UserRole.RECRUITER,
    )
    not_owner_token = _create_user_and_login(
        client,
        db_session,
        email="other.recruiter@example.com",
        role=UserRole.RECRUITER,
    )
    recruit_user = create_user(
        db_session,
        email="recruit.to.add@example.com",
        password="StrongPass123!",
        full_name="Recruit To Add",
        role=UserRole.RECRUITER,
    )
    company_response = client.post(
        "/api/v1/companies",
        json={"name": "Owned Company"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    forbidden_response = client.post(
        f"/api/v1/companies/{company_id}/recruiters",
        json={"recruiter_user_id": recruit_user.id},
        headers={"Authorization": f"Bearer {not_owner_token}"},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"] == "Only company owner can add recruiters."

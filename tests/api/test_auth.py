from fastapi.testclient import TestClient


def test_register_creates_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "register@example.com",
            "password": "StrongPass123!",
            "full_name": "Register User",
        },
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["email"] == "register@example.com"
    assert payload["full_name"] == "Register User"
    assert payload["role"] == "candidate"
    assert payload["is_activated"] is True
    assert "hashed_password" not in payload


def test_register_conflict_for_duplicate_email(client: TestClient) -> None:
    request_payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123!",
        "full_name": "Duplicate User",
    }

    first_response = client.post("/api/v1/auth/register", json=request_payload)
    second_response = client.post("/api/v1/auth/register", json=request_payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "User with this email already exists."


def test_login_returns_token_pair_shape(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPass123!",
            "full_name": "Login User",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "StrongPass123!",
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"


def test_login_returns_unauthorized_for_wrong_password(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "StrongPass123!",
            "full_name": "Wrong Password User",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."

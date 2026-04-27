from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt

from app.core.security import ALGORITHM
from app.core.config import settings


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


def test_refresh_returns_new_token_pair(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "StrongPass123!",
            "full_name": "Refresh User",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "StrongPass123!"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"


def test_refresh_rejects_invalid_refresh_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token."


def test_refresh_rejects_access_token_with_invalid_token_type(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh-type@example.com",
            "password": "StrongPass123!",
            "full_name": "Refresh Type User",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh-type@example.com", "password": "StrongPass123!"},
    )
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token type."


def test_refresh_rejects_expired_refresh_token(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh-expired@example.com",
            "password": "StrongPass123!",
            "full_name": "Refresh Expired User",
        },
    )
    expired_payload = {
        "sub": "refresh-expired@example.com",
        "type": "refresh",
        "exp": datetime.now(UTC) - timedelta(minutes=5),
    }
    expired_refresh_token = jwt.encode(expired_payload, settings.secret_key, algorithm=ALGORITHM)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_refresh_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token expired."

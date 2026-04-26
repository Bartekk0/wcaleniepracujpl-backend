from fastapi.testclient import TestClient


def test_me_returns_user_shape(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "StrongPass123!",
            "full_name": "Me User",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "StrongPass123!"},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["email"] == "me@example.com"
    assert payload["full_name"] == "Me User"
    assert payload["role"] == "candidate"
    assert payload["is_activated"] is True


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_me_rejects_refresh_token_type(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "me-refresh@example.com",
            "password": "StrongPass123!",
            "full_name": "Me Refresh User",
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "me-refresh@example.com", "password": "StrongPass123!"},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token type."

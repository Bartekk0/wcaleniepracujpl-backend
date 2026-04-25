from fastapi.testclient import TestClient


def test_login_returns_token_pair_shape(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login")
    payload = response.json()

    assert response.status_code == 200
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["token_type"] == "bearer"

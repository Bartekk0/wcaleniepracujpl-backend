from fastapi.testclient import TestClient


def test_me_returns_user_shape(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    payload = response.json()

    assert response.status_code == 200
    assert payload["id"] == 0
    assert payload["email"] == "todo@example.com"
    assert payload["role"] == "candidate"
    assert payload["is_activated"] is True

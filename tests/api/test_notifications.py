from fastapi.testclient import TestClient


def test_notifications_health_returns_status_and_flag(client: TestClient) -> None:
    response = client.get("/api/v1/notifications/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "notifications_enabled" in body
    assert isinstance(body["notifications_enabled"], bool)

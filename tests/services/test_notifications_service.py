from app.domains.notifications import service as notifications_service


def test_should_enqueue_tasks_uses_explicit_settings_flag(monkeypatch) -> None:
    monkeypatch.setattr(notifications_service.settings, "notifications_enabled", True)
    assert notifications_service._should_enqueue_tasks() is True

    monkeypatch.setattr(notifications_service.settings, "notifications_enabled", False)
    assert notifications_service._should_enqueue_tasks() is False

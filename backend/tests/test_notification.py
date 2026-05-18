import pytest
from backend.app.harness.notification import (
    Notification,
    LoggingNotificationService,
    CompositeNotificationService,
)


class TestNotification:
    def test_notification_defaults(self):
        notif = Notification(type="approval_required")
        assert notif.type == "approval_required"
        assert notif.priority == "normal"
        assert notif.timestamp

    def test_notification_with_payload(self):
        notif = Notification(
            type="security_alert",
            priority="critical",
            payload={"action": "deploy_prod", "actor": "agent-1"},
        )
        assert notif.priority == "critical"
        assert notif.payload["action"] == "deploy_prod"


class TestLoggingNotification:
    @pytest.mark.asyncio
    async def test_logging_service_returns_true(self):
        svc = LoggingNotificationService()
        result = await svc.send(
            Notification(type="test", priority="low", payload={"msg": "test"})
        )
        assert result is True


class TestCompositeNotification:
    @pytest.mark.asyncio
    async def test_composite_delegates_to_all(self):
        svc = CompositeNotificationService([
            LoggingNotificationService(),
            LoggingNotificationService(),
        ])
        result = await svc.send(
            Notification(type="test", priority="normal")
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_composite_empty_list(self):
        svc = CompositeNotificationService([])
        result = await svc.send(
            Notification(type="test", priority="normal")
        )
        assert result is False

import asyncio
import json
import smtplib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import get_settings


@dataclass
class Notification:
    type: str
    priority: str = "normal"
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class NotificationService(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        ...


class SlackNotificationService(NotificationService):
    def __init__(self, webhook_url: Optional[str] = None):
        settings = get_settings()
        self.webhook_url = webhook_url or settings.SLACK_WEBHOOK_URL
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    async def send(self, notification: Notification) -> bool:
        if not self.webhook_url:
            return False

        color = {
            "low": "#36a64f",
            "normal": "#439fe0",
            "high": "#ffcc00",
            "critical": "#ff0000",
        }.get(notification.priority, "#cccccc")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"[{notification.type.upper()}] {notification.priority.upper()} Priority",
                    "fields": [
                        {"title": k, "value": str(v)[:200], "short": True}
                        for k, v in notification.payload.items()
                    ],
                    "footer": f"Harness Control Plane · {notification.timestamp}",
                }
            ]
        }

        try:
            response = await self._client.post(self.webhook_url, json=payload)
            return response.is_success
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class EmailNotificationService(NotificationService):
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
    ):
        settings = get_settings()
        self.smtp_host = smtp_host or settings.SMTP_HOST
        self.smtp_port = smtp_port or settings.SMTP_PORT

    async def send(self, notification: Notification) -> bool:
        if not self.smtp_host:
            return False

        msg = MIMEText(
            json.dumps(notification.payload, indent=2, default=str),
            "plain",
        )
        msg["Subject"] = (
            f"[Harness] {notification.type.upper()} — "
            f"{notification.priority.upper()} Priority"
        )
        msg["From"] = "harness@localhost"
        msg["To"] = "operator@localhost"

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._send_sync(msg),
            )
            return True
        except Exception:
            return False

    def _send_sync(self, msg: MIMEText) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.send_message(msg)


class CompositeNotificationService(NotificationService):
    def __init__(self, services: List[NotificationService]):
        self.services = services

    async def send(self, notification: Notification) -> bool:
        results = await asyncio.gather(
            *(s.send(notification) for s in self.services),
            return_exceptions=True,
        )
        return any(r is True for r in results)


class LoggingNotificationService(NotificationService):
    async def send(self, notification: Notification) -> bool:
        asyncio.ensure_future(self._log(notification))
        return True

    async def _log(self, notification: Notification) -> None:
        from backend.app.models.audit import AuditEntry as AuditModel
        # Log notification as an audit event for traceability
        pass

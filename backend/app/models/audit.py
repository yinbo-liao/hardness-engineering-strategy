import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base


class AuditEntry(Base):
    __tablename__ = "harness_audit_log"

    entry_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"aud_{uuid.uuid4().hex[:12]}",
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(String(32), default="pending")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_granted: Mapped[bool] = mapped_column(Boolean, nullable=True)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

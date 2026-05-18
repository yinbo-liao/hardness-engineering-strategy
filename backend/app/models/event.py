import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base


class HarnessEvent(Base):
    __tablename__ = "harness_events"
    __table_args__ = (UniqueConstraint("task_id", "sequence"),)

    event_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"evt_{uuid.uuid4().hex[:12]}",
    )
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    @staticmethod
    def idx_events_task_sequence():
        return "CREATE INDEX IF NOT EXISTS idx_events_task_sequence ON harness_events(task_id, sequence)"

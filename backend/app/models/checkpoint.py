import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base


class Checkpoint(Base):
    __tablename__ = "harness_checkpoints"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:12]}"
    )
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_log: Mapped[list] = mapped_column(JSON, default=list)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

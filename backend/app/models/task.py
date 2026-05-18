import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "harness_tasks"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"task_{uuid.uuid4().hex[:12]}"
    )
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, default="code")
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=5)
    deps: Mapped[list] = mapped_column(JSON, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=3)
    max_iterations: Mapped[int] = mapped_column(Integer, default=5)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_log: Mapped[list] = mapped_column(JSON, default=list)
    checkpoint_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

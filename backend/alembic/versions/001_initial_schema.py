"""Initial schema — harness core tables with pgvector

Revision ID: 001
Revises: None
Create Date: 2026-05-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "harness_tasks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("description", sa.String(1024), nullable=False),
        sa.Column("task_type", sa.String(32), nullable=False, server_default="code"),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="taskstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), default=5),
        sa.Column("deps", sa.JSON(), default=list),
        sa.Column("retry_count", sa.Integer(), default=3),
        sa.Column("max_iterations", sa.Integer(), default=5),
        sa.Column("current_iteration", sa.Integer(), default=0),
        sa.Column("timeout_seconds", sa.Integer(), default=300),
        sa.Column("cost", sa.Float(), default=0.0),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_log", sa.JSON(), default=list),
        sa.Column("checkpoint_data", sa.JSON(), default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "harness_checkpoints",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), nullable=False, index=True),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("task_status", sa.String(32), nullable=False),
        sa.Column("error_log", sa.JSON(), default=list),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_checkpoints_task",
        "harness_checkpoints",
        ["task_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "harness_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), nullable=False, index=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.UniqueConstraint("task_id", "sequence"),
    )
    op.create_index(
        "idx_events_task_sequence",
        "harness_events",
        ["task_id", "sequence"],
    )

    op.create_table(
        "harness_audit_log",
        sa.Column("entry_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, index=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False, server_default="system"),
        sa.Column("params", sa.JSON(), default=dict),
        sa.Column("result", sa.String(32), server_default="pending"),
        sa.Column("risk_level", sa.String(16), server_default="low"),
        sa.Column("approval_required", sa.Boolean(), default=False),
        sa.Column("approval_granted", sa.Boolean(), nullable=True),
        sa.Column("integrity_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "code_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), default=dict),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("code_embeddings")
    op.drop_table("harness_audit_log")
    op.drop_table("harness_events")
    op.drop_table("harness_checkpoints")
    op.drop_table("harness_tasks")
    op.execute("DROP TYPE IF EXISTS taskstatus")

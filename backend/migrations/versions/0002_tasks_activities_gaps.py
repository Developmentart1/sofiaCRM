"""Fill the gaps between the existing ``tasks``/``activities`` tables and the
frontend contract (``frontend/src/lib/types/api.ts``).

Revision ID: 0002_tasks_activities_gaps
Revises: 0001_initial
Create Date: 2026-08-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_tasks_activities_gaps"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── activities ─────────────────────────────────────────────────
    # task_id: link an activity (e.g. a completed task log) to a task.
    # NOTE: SQLite cannot ALTER-ADD a column with a FOREIGN KEY constraint
    # (no support for ALTER of constraints). We add the column as a plain
    # String; the ORM model still declares the FK for metadata/create_all.
    op.add_column(
        "activities",
        sa.Column("task_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "activities",
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
    )
    # occurred_at: the frontend's canonical "when it happened" timestamp.
    # ``scheduled_at`` (existing) still exists but represents a planned time;
    # we introduce ``occurred_at`` and backfill it from ``scheduled_at`` so no
    # existing data is lost. New activities always set occurred_at explicitly.
    op.add_column(
        "activities",
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        "UPDATE activities SET occurred_at = scheduled_at "
        "WHERE occurred_at IS NULL AND scheduled_at IS NOT NULL"
    )
    op.create_index("ix_activities_task_id", "activities", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_activities_task_id", table_name="activities")
    op.drop_column("activities", "occurred_at")
    op.drop_column("activities", "duration_minutes")
    op.drop_column("activities", "task_id")

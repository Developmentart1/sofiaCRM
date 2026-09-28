"""Add ``conditions_json`` to ``automation_rules`` so the automation engine can
store rule conditions (a JSON array of ``{field, op, value}``) directly on the
rule instead of encoding them as a special action.

Revision ID: 0003_automation_conditions
Revises: 0002_tasks_activities_gaps
Create Date: 2026-08-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_automation_conditions"
down_revision = "0002_tasks_activities_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "automation_rules",
        sa.Column("conditions_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("automation_rules", "conditions_json")

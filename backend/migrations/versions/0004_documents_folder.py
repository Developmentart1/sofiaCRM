"""Add ``folder`` to ``documents`` so users can organize uploaded files.

Revision ID: 0004_documents_folder
Revises: 0003_automation_conditions
Create Date: 2026-08-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_documents_folder"
down_revision = "0003_automation_conditions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("folder", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "folder")

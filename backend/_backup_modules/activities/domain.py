"""Activity + Task ORM models (spec sections 5.9 and 5.10)."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ActivityType(StrEnum):
    CALL = "call"
    EMAIL = "email"
    MESSAGE = "message"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"
    DOCUMENT = "document"
    STAGE_CHANGE = "stage_change"
    STATUS_CHANGE = "status_change"
    PAYMENT = "payment"
    SYSTEM = "system"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    performed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        Index("ix_activity_org_opportunity_time", "organization_id", "opportunity_id", "occurred_at"),
        Index("ix_activity_org_contact_time", "organization_id", "contact_id", "occurred_at"),
        Index("ix_activity_org_assigned_time", "organization_id", "assigned_user_id", "occurred_at"),
    )

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TaskStatus.PENDING.value, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", index=True)

    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)

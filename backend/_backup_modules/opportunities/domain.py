"""Opportunity ORM model. The core business entity (spec section 5.8)."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class OpportunityStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    DISCARDED = "discarded"


class OpportunityPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # RB-001: organization_id NOT NULL (handled by nullable=False above).

    contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")
    estimated_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weighted_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # probability 0..100 — overridable per RB-009.
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default=OpportunityPriority.NORMAL.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=OpportunityStatus.OPEN.value, index=True
    )

    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("lead_sources.id", ondelete="SET NULL"), nullable=True
    )

    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    won_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    lost_reason_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("lost_reasons.id", ondelete="SET NULL"), nullable=True
    )
    lost_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    next_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    entered_stage_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # RB-002: assigned_user_id NOT NULL if status='open'.
    # SQLite has no check constraints across columns without triggers; we
    # enforce this at the service layer.
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    team_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    is_stuck: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_opportunity_org_status", "organization_id", "status"),
        Index("ix_opportunity_org_pipeline_stage", "organization_id", "pipeline_id", "stage_id"),
        Index("ix_opportunity_org_assigned", "organization_id", "assigned_user_id"),
    )

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)


class LostReason(Base):
    __tablename__ = "lost_reasons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)


class LeadSource(Base):
    __tablename__ = "lead_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)

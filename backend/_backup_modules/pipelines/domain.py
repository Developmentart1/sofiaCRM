"""Pipeline and Stage ORM models. A pipeline owns an ordered list of stages."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class StageType(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    DISCARDED = "discarded"


class EntityType(StrEnum):
    OPPORTUNITY = "opportunity"
    LEAD = "lead"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, default=EntityType.OPPORTUNITY.value)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    stages: Mapped[list[Stage]] = relationship(
        "Stage", back_populates="pipeline", order_by="Stage.position", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_pipeline_org_default", "organization_id", "is_default"),)

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pipeline_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_type: Mapped[str] = mapped_column(String(16), nullable=False, default=StageType.OPEN.value)
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=10, index=True)
    maximum_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    pipeline: Mapped[Pipeline] = relationship("Pipeline", back_populates="stages")

    __table_args__ = (Index("ix_stage_pipeline_pos", "pipeline_id", "position"),)

    @property
    def uuid(self) -> UUID:
        return UUID(self.id)

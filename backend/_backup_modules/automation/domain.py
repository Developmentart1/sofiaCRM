"""Automation rule engine ORM models.

Design (spec section 16 / 17):

  automation_rule          ← top level, with trigger_event_type and is_active
  automation_condition      ← JSON predicates evaluated against the trigger payload
  automation_action         ← one or more side-effects to run on a match
  automation_execution      ← idempotency cache: every (rule_id, event_id) is recorded once

Actions support up to depth MAX_DEPTH=5 chained rules: rule A triggers rule B,
recursion is bounded by the depth counter and by the per-(rule, event) execution
cache.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
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


class AutomationCondition(Base):
    __tablename__ = "automation_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(16), nullable=False)  # eq, ne, gt, lt, in, contains
    value_json: Mapped[str] = mapped_column(Text, nullable=False)


class AutomationAction(Base):
    __tablename__ = "automation_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AutomationExecution(Base):
    """Idempotency: an (event_id, rule_id) pair may execute at most once."""

    __tablename__ = "automation_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index(
            "uq_automation_exec_rule_event",
            "rule_id",
            "event_id",
            unique=True,
        ),
        Index("ix_automation_exec_org_time", "organization_id", "executed_at"),
    )

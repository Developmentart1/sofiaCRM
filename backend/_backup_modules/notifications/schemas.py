"""Notification Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    title: str = Field(min_length=2, max_length=200)
    body: str | None = None
    category: str = Field(default="general", max_length=40)
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    user_id: UUID
    title: str
    body: str | None
    category: str
    related_entity_type: str | None
    related_entity_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

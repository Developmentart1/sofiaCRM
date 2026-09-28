"""AuditLog Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    request_ip: str | None
    user_agent: str | None
    metadata_json: dict[str, Any] | None
    occurred_at: datetime

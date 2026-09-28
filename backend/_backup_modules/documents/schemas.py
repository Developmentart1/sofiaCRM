"""Document Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    description: str | None
    contact_id: UUID | None
    opportunity_id: UUID | None
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentMetadata(BaseModel):
    """Returned by the upload endpoint with a signed download URL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    download_url: str
    expires_in_seconds: int

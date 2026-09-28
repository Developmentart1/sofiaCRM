"""Organization Pydantic v2 schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizationCreate(BaseModel):
    """Payload for creating a tenant. The first user (admin) is created alongside."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    timezone: str = Field(default="America/Mexico_City", max_length=64)
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    locale: str = Field(default="es-MX", max_length=8)
    admin_email: str = Field(min_length=3, max_length=255)
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str = Field(min_length=2, max_length=160)

    @field_validator("currency", "admin_email", "admin_full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class OrganizationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    locale: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    timezone: str
    currency: str
    locale: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

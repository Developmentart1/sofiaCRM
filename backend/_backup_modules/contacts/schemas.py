"""Contact & Company Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    tax_id: str | None = Field(default=None, max_length=40)
    industry: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=255)
    size: str | None = Field(default=None, max_length=40)
    notes: str | None = None
    owner_user_id: UUID | None = None


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    tax_id: str | None = Field(default=None, max_length=40)
    industry: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=255)
    size: str | None = Field(default=None, max_length=40)
    notes: str | None = None
    owner_user_id: UUID | None = None
    is_active: bool | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    tax_id: str | None
    industry: str | None
    website: str | None
    size: str | None
    notes: str | None
    owner_user_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_type: str = Field(default="persona_fisica", pattern=r"^(persona_fisica|persona_moral)$")
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    job_title: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    company_id: UUID | None = None
    owner_user_id: UUID | None = None
    score: float = Field(default=0.0, ge=0.0, le=100.0)


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    job_title: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    company_id: UUID | None = None
    owner_user_id: UUID | None = None
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    is_active: bool | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    contact_type: str
    full_name: str
    email: str | None
    phone: str | None
    job_title: str | None
    source: str | None
    company_id: UUID | None
    owner_user_id: UUID | None
    score: float
    is_active: bool
    last_activity_at: datetime | None
    next_activity_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ContactMergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    winner_id: UUID
    loser_id: UUID


class DuplicateCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact: ContactRead
    match_field: str
    match_value: str

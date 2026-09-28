"""Contact Pydantic schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=300)
    legal_name: str | None = None
    rfc: str | None = Field(default=None, max_length=13)
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    industry: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip: str | None = None
    notes: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    legal_name: str | None = None
    rfc: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    industry: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(default="PF", pattern="^(PF|PM)$")
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str | None = None
    legal_name: str | None = None
    rfc: str | None = Field(default=None, max_length=13)
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    company_id: str | None = None
    source_id: str | None = None
    tags: str | None = None


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = Field(default=None, min_length=1, max_length=150)
    last_name: str | None = None
    legal_name: str | None = None
    rfc: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    company_id: str | None = None
    source_id: str | None = None
    tags: str | None = None
    status: str | None = None
    assigned_user_id: str | None = None
    notes: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    company_id: str | None = None
    type: str
    first_name: str
    last_name: str | None = None
    legal_name: str | None = None
    rfc: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    position: str | None = None
    source_id: str | None = None
    status: str
    tags: str | None = None
    notes: str | None = None
    assigned_user_id: str | None = None
    last_activity_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

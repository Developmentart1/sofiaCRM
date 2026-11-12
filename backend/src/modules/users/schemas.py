"""User Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="asesor")
    phone: str | None = Field(default=None, max_length=40)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: str | None = None
    phone: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None


class UserPasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: str
    phone: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_slug: str = Field(min_length=2, max_length=64)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CompanyLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_slug: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead

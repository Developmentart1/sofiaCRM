"""Task Pydantic schemas — mirror the frontend ``Task``/``TaskCreate`` types.

The frontend sends empty strings for optional IDs/dates (``"contact_id": ""``),
so we coerce ``""`` → ``None`` before validation.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _empty_to_none(value: object) -> object:
    if value == "":
        return None
    return value


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    status: str = "pending"
    priority: str = "medium"
    due_date: datetime | None = None
    contact_id: str | None = None
    opportunity_id: str | None = None
    company_id: str | None = None
    owner_id: str | None = None

    @field_validator(
        "due_date", "contact_id", "opportunity_id", "company_id", "owner_id", mode="before"
    )
    @classmethod
    def _coerce_empty(cls, value: object) -> object:
        return _empty_to_none(value)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    contact_id: str | None = None
    opportunity_id: str | None = None
    company_id: str | None = None
    owner_id: str | None = None

    @field_validator(
        "due_date", "contact_id", "opportunity_id", "company_id", "owner_id", mode="before"
    )
    @classmethod
    def _coerce_empty(cls, value: object) -> object:
        return _empty_to_none(value)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: datetime | None = None
    completed_at: datetime | None = None
    contact_id: str | None = None
    contact_name: str | None = None
    opportunity_id: str | None = None
    opportunity_name: str | None = None
    company_id: str | None = None
    company_name: str | None = None
    owner_id: str
    owner_name: str | None = None
    created_at: datetime
    updated_at: datetime

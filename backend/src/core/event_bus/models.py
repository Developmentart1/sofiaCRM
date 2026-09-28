"""Typed Pydantic v2 payloads for every event in the system (spec section 16).

All payloads inherit from BaseEvent and carry organization_id so handlers
never have to guess which tenant the event belongs to.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    """Common envelope fields for every event payload."""

    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.utcnow())


# --- Contact events ---

class ContactCreated(BaseEvent):
    event_type: Literal["contact.created"] = "contact.created"
    contact_id: UUID
    full_name: str
    email_normalized: str | None = None


class ContactUpdated(BaseEvent):
    event_type: Literal["contact.updated"] = "contact.updated"
    contact_id: UUID
    changed_fields: list[str] = Field(default_factory=list)


class ContactMerged(BaseEvent):
    event_type: Literal["contact.merged"] = "contact.merged"
    winner_id: UUID
    loser_id: UUID


# --- Company events ---

class CompanyCreated(BaseEvent):
    event_type: Literal["company.created"] = "company.created"
    company_id: UUID
    name: str


class CompanyUpdated(BaseEvent):
    event_type: Literal["company.updated"] = "company.updated"
    company_id: UUID


# --- Pipeline / stage events ---

class PipelineCreated(BaseEvent):
    event_type: Literal["pipeline.created"] = "pipeline.created"
    pipeline_id: UUID
    name: str


class StageCreated(BaseEvent):
    event_type: Literal["stage.created"] = "stage.created"
    stage_id: UUID
    pipeline_id: UUID
    name: str


# --- Opportunity events ---

class OpportunityCreated(BaseEvent):
    event_type: Literal["opportunity.created"] = "opportunity.created"
    opportunity_id: UUID
    title: str
    pipeline_id: UUID
    stage_id: UUID
    value: float
    currency: str
    assigned_user_id: UUID | None = None


class OpportunityStageChanged(BaseEvent):
    event_type: Literal["opportunity.stage_changed"] = "opportunity.stage_changed"
    opportunity_id: UUID
    from_stage_id: UUID | None
    to_stage_id: UUID
    entered_stage_at: datetime


class OpportunityAssigneeChanged(BaseEvent):
    event_type: Literal["opportunity.assignee_changed"] = "opportunity.assignee_changed"
    opportunity_id: UUID
    from_user_id: UUID | None
    to_user_id: UUID | None


class OpportunityValueChanged(BaseEvent):
    event_type: Literal["opportunity.value_changed"] = "opportunity.value_changed"
    opportunity_id: UUID
    from_value: float
    to_value: float
    currency: str


class OpportunityWon(BaseEvent):
    event_type: Literal["opportunity.won"] = "opportunity.won"
    opportunity_id: UUID
    final_value: float
    currency: str


class OpportunityLost(BaseEvent):
    event_type: Literal["opportunity.lost"] = "opportunity.lost"
    opportunity_id: UUID
    lost_reason: str


class OpportunityDiscarded(BaseEvent):
    event_type: Literal["opportunity.discarded"] = "opportunity.discarded"
    opportunity_id: UUID
    discarded_reason: str


# --- Task / activity events ---

class TaskCreated(BaseEvent):
    event_type: Literal["task.created"] = "task.created"
    task_id: UUID
    title: str
    due_at: datetime | None
    assigned_user_id: UUID | None
    opportunity_id: UUID | None = None


class TaskCompleted(BaseEvent):
    event_type: Literal["task.completed"] = "task.completed"
    task_id: UUID


class TaskOverdue(BaseEvent):
    event_type: Literal["task.overdue"] = "task.overdue"
    task_id: UUID
    due_at: datetime


class ActivityCreated(BaseEvent):
    event_type: Literal["activity.created"] = "activity.created"
    activity_id: UUID
    activity_type: str
    subject: str
    opportunity_id: UUID | None = None
    contact_id: UUID | None = None
    assigned_user_id: UUID | None = None


# --- Documents ---

class DocumentUploaded(BaseEvent):
    event_type: Literal["document.uploaded"] = "document.uploaded"
    document_id: UUID
    filename: str
    size_bytes: int
    contact_id: UUID | None = None
    opportunity_id: UUID | None = None


# Discriminated union of all event payloads for type-safe handlers.
EventEnvelope = Annotated[
    ContactCreated
    | ContactUpdated
    | ContactMerged
    | CompanyCreated
    | CompanyUpdated
    | PipelineCreated
    | StageCreated
    | OpportunityCreated
    | OpportunityStageChanged
    | OpportunityAssigneeChanged
    | OpportunityValueChanged
    | OpportunityWon
    | OpportunityLost
    | OpportunityDiscarded
    | TaskCreated
    | TaskCompleted
    | TaskOverdue
    | ActivityCreated
    | DocumentUploaded,
    Field(discriminator="event_type"),
]

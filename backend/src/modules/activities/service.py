"""Activities service — append-only timeline with tenant isolation.

System activities (``stage_change``, ``created``, ``updated``,
``task_completed``) are never created or deleted through the API; they are
written as side effects of other modules (see ``record_stage_change``).
"""
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from core.errors import ForbiddenError, NotFoundError, ValidationError
from core.event_bus import ActivityCreated, get_bus
from core.pagination import PaginatedResponse
from core.tenant import current_org_id, current_user_id_or_none
from modules.contacts.domain import Company, Contact
from modules.opportunities.domain import Opportunity
from modules.tasks.domain import Task
from modules.users.domain import User
from .domain import Activity
from .schemas import ActivityCreate, ActivityRead, MANUAL_ACTIVITY_TYPES


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def _validate_refs(
        self,
        contact_id: str | None,
        opportunity_id: str | None,
        company_id: str | None,
        task_id: str | None,
    ) -> None:
        org = current_org_id()
        if contact_id:
            if not self.db.query(Contact).filter(
                Contact.id == contact_id,
                Contact.organization_id == org,
                Contact.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"contact '{contact_id}' not found")
        if company_id:
            if not self.db.query(Company).filter(
                Company.id == company_id,
                Company.organization_id == org,
                Company.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"company '{company_id}' not found")
        if opportunity_id:
            if not self.db.query(Opportunity).filter(
                Opportunity.id == opportunity_id,
                Opportunity.organization_id == org,
                Opportunity.deleted_at.is_(None),
            ).first():
                raise NotFoundError(f"opportunity '{opportunity_id}' not found")
        if task_id:
            if not self.db.query(Task).filter(
                Task.id == task_id, Task.organization_id == org
            ).first():
                raise NotFoundError(f"task '{task_id}' not found")

    def _base_query(self):
        org = current_org_id()
        return (
            self.db.query(
                Activity,
                Contact.first_name,
                Contact.last_name,
                Opportunity.name,
                Company.name,
                User.full_name,
            )
            .outerjoin(Contact, and_(Contact.id == Activity.contact_id, Contact.organization_id == org))
            .outerjoin(
                Opportunity, and_(Opportunity.id == Activity.opportunity_id, Opportunity.organization_id == org)
            )
            .outerjoin(Company, and_(Company.id == Activity.company_id, Company.organization_id == org))
            .outerjoin(User, User.id == Activity.user_id)
            .filter(Activity.organization_id == org)
        )

    def _to_read(
        self,
        activity: Activity,
        contact_first: str | None,
        contact_last: str | None,
        opp_name: str | None,
        company_name: str | None,
        user_name: str | None,
    ) -> ActivityRead:
        metadata: dict[str, str | int | float | bool | None] | None = None
        if activity.metadata_json:
            try:
                parsed = json.loads(activity.metadata_json)
                if isinstance(parsed, dict):
                    metadata = parsed
            except (ValueError, TypeError):
                metadata = None
        contact_name = " ".join(p for p in (contact_first, contact_last) if p).strip() or None
        return ActivityRead(
            id=activity.id,
            type=activity.type,
            subject=activity.subject or "",
            body=activity.body,
            occurred_at=activity.occurred_at or activity.created_at,
            duration_minutes=activity.duration_minutes,
            contact_id=activity.contact_id,
            contact_name=contact_name,
            opportunity_id=activity.opportunity_id,
            opportunity_name=opp_name,
            company_id=activity.company_id,
            company_name=company_name,
            task_id=activity.task_id,
            user_id=activity.user_id,
            user_name=user_name,
            metadata=metadata,
            created_at=activity.created_at,
        )

    def _read_one(self, activity_id: str) -> ActivityRead:
        row = self._base_query().filter(Activity.id == activity_id).first()
        if not row:
            raise NotFoundError(f"activity '{activity_id}' not found")
        return self._to_read(*row)

    def _get_orm(self, activity_id: str) -> Activity:
        org = current_org_id()
        activity = self.db.query(Activity).filter(
            Activity.id == activity_id, Activity.organization_id == org
        ).first()
        if not activity:
            raise NotFoundError(f"activity '{activity_id}' not found")
        return activity

    def list_activities(
        self,
        *,
        type: str | None = None,
        contact_id: str | None = None,
        opportunity_id: str | None = None,
        company_id: str | None = None,
        user_id: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ActivityRead]:
        q = self._base_query()
        if type:
            q = q.filter(Activity.type == type)
        if contact_id:
            q = q.filter(Activity.contact_id == contact_id)
        if opportunity_id:
            q = q.filter(Activity.opportunity_id == opportunity_id)
        if company_id:
            q = q.filter(Activity.company_id == company_id)
        if user_id:
            q = q.filter(Activity.user_id == user_id)
        if from_ is not None:
            q = q.filter(Activity.occurred_at >= from_)
        if to is not None:
            q = q.filter(Activity.occurred_at <= to)

        total = q.count()
        rows = (
            q.order_by(Activity.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = [self._to_read(*row) for row in rows]
        return PaginatedResponse.of(items=items, total=total, page=page, page_size=page_size)

    def list_recent(self, *, limit: int = 10) -> list[ActivityRead]:
        """Most recent activities of the org (dashboard widget)."""
        rows = (
            self._base_query()
            .order_by(Activity.occurred_at.desc(), Activity.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_read(*row) for row in rows]

    def create_activity(self, data: ActivityCreate, current_user_id: str) -> ActivityRead:
        if data.type not in MANUAL_ACTIVITY_TYPES:
            raise ValidationError(
                f"activity type '{data.type}' cannot be created via API",
                details={"type": data.type},
            )
        self._validate_refs(data.contact_id, data.opportunity_id, data.company_id, data.task_id)

        activity = Activity(
            organization_id=current_org_id(),
            contact_id=data.contact_id,
            company_id=data.company_id,
            opportunity_id=data.opportunity_id,
            task_id=data.task_id,
            user_id=current_user_id,
            type=data.type,
            subject=data.subject,
            body=data.body,
            metadata_json=json.dumps(data.metadata) if data.metadata else None,
            occurred_at=data.occurred_at or _now(),
            duration_minutes=data.duration_minutes,
        )
        self.db.add(activity)
        self.db.flush()
        get_bus().publish(
            ActivityCreated(
                organization_id=UUID(current_org_id()),
                activity_id=UUID(activity.id),
                activity_type=activity.type,
                subject=activity.subject or "",
                opportunity_id=UUID(activity.opportunity_id) if activity.opportunity_id else None,
                contact_id=UUID(activity.contact_id) if activity.contact_id else None,
                assigned_user_id=UUID(current_user_id),
            ),
            db=self.db,
        )
        self.db.commit()
        return self._read_one(activity.id)

    def delete_activity(self, activity_id: str) -> None:
        activity = self._get_orm(activity_id)
        if activity.type not in MANUAL_ACTIVITY_TYPES:
            raise ForbiddenError(
                f"system activity '{activity.type}' cannot be deleted",
                details={"type": activity.type},
            )
        self.db.delete(activity)
        self.db.commit()


def record_stage_change(event, db: Session) -> None:
    """Register a ``stage_change`` activity for an ``OpportunityStageChanged`` event.

    Runs synchronously inside the publisher's transaction (see the bus
    ``publish``). The actor is the authenticated user when available, falling
    back to the opportunity's assigned user. If neither exists the activity is
    skipped rather than violating the ``user_id`` NOT NULL constraint.
    """
    opp = db.query(Opportunity).filter(
        Opportunity.id == event.opportunity_id.hex,
        Opportunity.organization_id == str(event.organization_id),
        Opportunity.deleted_at.is_(None),
    ).first()
    if not opp:
        return

    user_id = current_user_id_or_none() or opp.assigned_user_id
    if user_id is None:
        return

    activity = Activity(
        organization_id=str(event.organization_id),
        opportunity_id=opp.id,
        contact_id=opp.contact_id,
        company_id=opp.company_id,
        user_id=user_id,
        type="stage_change",
        subject="Cambio de etapa",
        body=opp.name,
        metadata_json=json.dumps(
            {
                "from_stage_id": str(event.from_stage_id) if event.from_stage_id else None,
                "to_stage_id": str(event.to_stage_id),
            }
        ),
        occurred_at=event.entered_stage_at or _now(),
    )
    db.add(activity)
    db.flush()

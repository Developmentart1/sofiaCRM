"""Tasks service — CRUD with tenant isolation, denormalized names and a
derived ``overdue`` status.

``overdue`` is never stored: a task is overdue when it is not completed/cancelled
and its due date is in the past. The read layer exposes that derived value as
``status`` so the frontend can filter with ``status === "overdue"``.
"""
from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.event_bus import TaskCompleted, TaskCreated, get_bus
from core.pagination import PaginatedResponse
from core.tenant import current_org_id
from modules.contacts.domain import Company, Contact
from modules.opportunities.domain import Opportunity
from modules.users.domain import User
from .domain import Task
from .schemas import TaskCreate, TaskRead, TaskUpdate

_COMPLETED_STATES = ("completed", "cancelled")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _combine_due(d: date | None, t: time | None) -> datetime | None:
    if d is None:
        return None
    return datetime.combine(d, t or time.min)


def _split_due(due: datetime | None) -> tuple[date | None, time | None]:
    if due is None:
        return None, None
    return due.date(), due.time()


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    # ── helpers ──────────────────────────────────────────

    def _validate_refs(
        self,
        contact_id: str | None,
        opportunity_id: str | None,
        company_id: str | None,
        owner_id: str | None,
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
        if owner_id:
            if not self.db.query(User).filter(
                User.id == owner_id, User.organization_id == org
            ).first():
                raise NotFoundError(f"user '{owner_id}' not found")

    def _base_query(self):
        org = current_org_id()
        return (
            self.db.query(
                Task,
                Contact.first_name,
                Contact.last_name,
                Opportunity.name,
                Company.name,
                User.full_name,
            )
            .outerjoin(Contact, and_(Contact.id == Task.contact_id, Contact.organization_id == org))
            .outerjoin(
                Opportunity, and_(Opportunity.id == Task.opportunity_id, Opportunity.organization_id == org)
            )
            .outerjoin(Company, and_(Company.id == Task.company_id, Company.organization_id == org))
            .outerjoin(User, User.id == Task.assigned_user_id)
            .filter(Task.organization_id == org)
        )

    def _to_read(
        self,
        task: Task,
        contact_first: str | None,
        contact_last: str | None,
        opp_name: str | None,
        company_name: str | None,
        owner_name: str | None,
    ) -> TaskRead:
        status = task.status
        if task.status not in _COMPLETED_STATES and task.due_date is not None and task.due_date < _today():
            status = "overdue"
        contact_name = " ".join(p for p in (contact_first, contact_last) if p).strip() or None
        return TaskRead(
            id=task.id,
            title=task.title,
            description=task.description,
            status=status,
            priority=task.priority,
            due_date=_combine_due(task.due_date, task.due_time),
            completed_at=task.completed_at,
            contact_id=task.contact_id,
            contact_name=contact_name,
            opportunity_id=task.opportunity_id,
            opportunity_name=opp_name,
            company_id=task.company_id,
            company_name=company_name,
            owner_id=task.assigned_user_id,
            owner_name=owner_name,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _read_one(self, task_id: str) -> TaskRead:
        row = self._base_query().filter(Task.id == task_id).first()
        if not row:
            raise NotFoundError(f"task '{task_id}' not found")
        return self._to_read(*row)

    def _get_orm(self, task_id: str) -> Task:
        org = current_org_id()
        task = self.db.query(Task).filter(
            Task.id == task_id, Task.organization_id == org
        ).first()
        if not task:
            raise NotFoundError(f"task '{task_id}' not found")
        return task

    # ── CRUD ─────────────────────────────────────────────

    def list_tasks(
        self,
        *,
        current_user_id: str,
        search: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        owner_id: str | None = None,
        contact_id: str | None = None,
        opportunity_id: str | None = None,
        company_id: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        view: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TaskRead]:
        q = self._base_query()
        today = _today()

        if search:
            like = f"%{search}%"
            q = q.filter(or_(Task.title.ilike(like), Task.description.ilike(like)))
        if status:
            if status == "overdue":
                q = q.filter(Task.status.notin_(_COMPLETED_STATES), Task.due_date < today)
            else:
                q = q.filter(Task.status == status)
        if priority:
            q = q.filter(Task.priority == priority)
        if owner_id:
            q = q.filter(Task.assigned_user_id == owner_id)
        if contact_id:
            q = q.filter(Task.contact_id == contact_id)
        if opportunity_id:
            q = q.filter(Task.opportunity_id == opportunity_id)
        if company_id:
            q = q.filter(Task.company_id == company_id)
        if due_before is not None:
            q = q.filter(Task.due_date <= due_before.date())
        if due_after is not None:
            q = q.filter(Task.due_date >= due_after.date())

        if view == "mine":
            q = q.filter(Task.assigned_user_id == current_user_id)
        elif view == "today":
            q = q.filter(Task.due_date == today)
        elif view == "overdue":
            q = q.filter(Task.status.notin_(_COMPLETED_STATES), Task.due_date < today)
        elif view == "upcoming":
            q = q.filter(Task.due_date >= today)

        total = q.count()
        rows = (
            q.order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = [self._to_read(*row) for row in rows]
        return PaginatedResponse.of(items=items, total=total, page=page, page_size=page_size)

    def list_upcoming(self, *, limit: int = 10) -> list[TaskRead]:
        """Pending/in-progress tasks due today or later, soonest first."""
        today = _today()
        rows = (
            self._base_query()
            .filter(Task.status.in_(("pending", "in_progress")), Task.due_date >= today)
            .order_by(Task.due_date.asc(), Task.due_time.asc(), Task.id.asc())
            .limit(limit)
            .all()
        )
        return [self._to_read(*row) for row in rows]

    def get_task(self, task_id: str) -> TaskRead:
        return self._read_one(task_id)

    def create_task(self, data: TaskCreate, current_user_id: str) -> TaskRead:
        self._validate_refs(data.contact_id, data.opportunity_id, data.company_id, data.owner_id)
        owner_id = data.owner_id or current_user_id
        due_date, due_time = _split_due(data.due_date)

        task = Task(
            organization_id=current_org_id(),
            contact_id=data.contact_id,
            company_id=data.company_id,
            opportunity_id=data.opportunity_id,
            assigned_user_id=owner_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=data.status,
            due_date=due_date,
            due_time=due_time,
        )
        if task.status == "completed":
            task.completed_at = _now()

        self.db.add(task)
        self.db.flush()
        get_bus().publish(
            TaskCreated(
                organization_id=UUID(current_org_id()),
                task_id=UUID(task.id),
                title=task.title,
                due_at=_combine_due(task.due_date, task.due_time),
                assigned_user_id=UUID(task.assigned_user_id),
                opportunity_id=UUID(task.opportunity_id) if task.opportunity_id else None,
            ),
            db=self.db,
        )
        self.db.commit()
        return self._read_one(task.id)

    def update_task(self, task_id: str, data: TaskUpdate) -> TaskRead:
        task = self._get_orm(task_id)
        updates = data.model_dump(exclude_unset=True)

        new_contact = updates.get("contact_id", task.contact_id)
        new_opportunity = updates.get("opportunity_id", task.opportunity_id)
        new_company = updates.get("company_id", task.company_id)
        new_owner = updates.get("owner_id", task.assigned_user_id)
        self._validate_refs(new_contact, new_opportunity, new_company, new_owner)

        was_completed = task.status == "completed"
        new_status = updates.get("status", task.status)

        if "title" in updates:
            task.title = updates["title"]
        if "description" in updates:
            task.description = updates["description"]
        if "priority" in updates:
            task.priority = updates["priority"]
        if "owner_id" in updates:
            task.assigned_user_id = updates["owner_id"]
        if "contact_id" in updates:
            task.contact_id = updates["contact_id"]
        if "opportunity_id" in updates:
            task.opportunity_id = updates["opportunity_id"]
        if "company_id" in updates:
            task.company_id = updates["company_id"]
        if "due_date" in updates:
            task.due_date, task.due_time = _split_due(updates["due_date"])

        task.status = new_status
        publish_completed = False
        if new_status == "completed":
            if not was_completed:
                task.completed_at = _now()
                publish_completed = True
            # already completed: idempotent, do not reset completed_at
        else:
            task.completed_at = None

        task.updated_at = _now()
        self.db.flush()
        if publish_completed:
            get_bus().publish(
                TaskCompleted(organization_id=UUID(current_org_id()), task_id=UUID(task.id)),
                db=self.db,
            )
        self.db.commit()
        return self._read_one(task.id)

    def delete_task(self, task_id: str) -> None:
        task = self._get_orm(task_id)
        self.db.delete(task)
        self.db.commit()

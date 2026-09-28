"""Test seeding helpers — raw SQL against the shared temp test DB."""
from datetime import date, datetime, time, timezone
from uuid import uuid4

import sqlalchemy as sa

from core.security import create_access_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_token(org_id: str, user_id: str, role: str = "admin") -> str:
    return create_access_token(subject=user_id, organization_id=org_id, role=role)


def insert_org(db, name: str = "Test Org") -> str:
    # organizations.id uses str(uuid4()) (dashed) in the ORM model.
    org_id = str(uuid4())
    db.execute(
        sa.text(
            "INSERT INTO organizations (id, name, slug, created_at, updated_at) "
            "VALUES (:id, :name, :slug, :t, :t)"
        ),
        {"id": org_id, "name": name, "slug": f"org-{org_id[:8]}", "t": _now()},
    )
    return org_id


def insert_user(db, org_id: str, role: str = "admin", email: str | None = None) -> str:
    # users.id uses str(uuid4()) (dashed) in the ORM model.
    user_id = str(uuid4())
    email = email or f"{uuid4().hex[:8]}@test.mx"
    db.execute(
        sa.text(
            "INSERT INTO users (id, organization_id, email, email_normalized, full_name, "
            "password_hash, role, created_at, updated_at) "
            "VALUES (:id, :org, :email, :email, :name, 'x', :role, :t, :t)"
        ),
        {"id": user_id, "org": org_id, "email": email, "name": f"User {user_id[:6]}", "role": role, "t": _now()},
    )
    return user_id


def insert_contact(db, org_id: str, first_name: str = "Contact") -> str:
    contact_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO contacts (id, organization_id, type, first_name, last_name, created_at, updated_at) "
            "VALUES (:id, :org, 'PF', :first, 'Test', :t, :t)"
        ),
        {"id": contact_id, "org": org_id, "first": first_name, "t": _now()},
    )
    return contact_id


def insert_company(db, org_id: str, name: str = "Company") -> str:
    company_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO companies (id, organization_id, name, created_at, updated_at) "
            "VALUES (:id, :org, :name, :t, :t)"
        ),
        {"id": company_id, "org": org_id, "name": name, "t": _now()},
    )
    return company_id


def insert_pipeline_and_stages(db, org_id: str) -> tuple[str, dict[str, str]]:
    pipeline_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO pipelines (id, organization_id, name, created_at, updated_at) "
            "VALUES (:id, :org, 'Pipeline', :t, :t)"
        ),
        {"id": pipeline_id, "org": org_id, "t": _now()},
    )
    stages: dict[str, str] = {}
    for stype, name, pos, prob in [
        ("open", "Open", 1, 20),
        ("won", "Won", 2, 100),
        ("lost", "Lost", 3, 0),
    ]:
        sid = uuid4().hex
        db.execute(
            sa.text(
                "INSERT INTO pipeline_stages (id, organization_id, pipeline_id, name, position, "
                "probability, stage_type, created_at, updated_at) "
                "VALUES (:id, :org, :pipe, :name, :pos, :prob, :stype, :t, :t)"
            ),
            {"id": sid, "org": org_id, "pipe": pipeline_id, "name": name, "pos": pos, "prob": prob, "stype": stype, "t": _now()},
        )
        stages[stype] = sid
    return pipeline_id, stages


def insert_opportunity(
    db,
    org_id: str,
    pipeline_id: str,
    stage_id: str,
    contact_id: str | None = None,
    assigned_user_id: str | None = None,
    name: str = "Opportunity",
) -> str:
    opp_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO opportunities (id, organization_id, pipeline_id, stage_id, name, "
            "contact_id, assigned_user_id, created_at, updated_at) "
            "VALUES (:id, :org, :pipe, :stage, :name, :contact, :owner, :t, :t)"
        ),
        {
            "id": opp_id,
            "org": org_id,
            "pipe": pipeline_id,
            "stage": stage_id,
            "name": name,
            "contact": contact_id,
            "owner": assigned_user_id,
            "t": _now(),
        },
    )
    return opp_id


def insert_task(
    db,
    org_id: str,
    assigned_user_id: str,
    title: str = "Task",
    status: str = "pending",
    due_date: date | None = None,
    due_time: time | None = None,
    contact_id: str | None = None,
    opportunity_id: str | None = None,
) -> str:
    task_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO tasks (id, organization_id, assigned_user_id, title, status, "
            "due_date, due_time, contact_id, opportunity_id, created_at, updated_at) "
            "VALUES (:id, :org, :owner, :title, :status, :due_date, :due_time, :contact, :opp, :t, :t)"
        ),
        {
            "id": task_id,
            "org": org_id,
            "owner": assigned_user_id,
            "title": title,
            "status": status,
            "due_date": due_date,
            "due_time": due_time,
            "contact": contact_id,
            "opp": opportunity_id,
            "t": _now(),
        },
    )
    return task_id


def insert_activity(
    db,
    org_id: str,
    user_id: str,
    type_: str = "note",
    opportunity_id: str | None = None,
    contact_id: str | None = None,
    occurred_at: datetime | None = None,
) -> str:
    activity_id = uuid4().hex
    db.execute(
        sa.text(
            "INSERT INTO activities (id, organization_id, user_id, type, opportunity_id, "
            "contact_id, occurred_at, created_at) "
            "VALUES (:id, :org, :user, :type, :opp, :contact, :occurred, :t)"
        ),
        {
            "id": activity_id,
            "org": org_id,
            "user": user_id,
            "type": type_,
            "opp": opportunity_id,
            "contact": contact_id,
            "occurred": occurred_at or _now(),
            "t": _now(),
        },
    )
    return activity_id

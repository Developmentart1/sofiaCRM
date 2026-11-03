"""Seed CRM-Splash with demo data across TWO organizations.

Uses raw SQL via the engine (no module imports needed beyond core) so the seed
is self-contained and never depends on ORM models. Each organization gets its
own pipeline, a varied set of users (admin/director/gerente/asesor/operaciones),
companies, contacts, opportunities and 3 example automation rules written in
the exact ``config_json``/``conditions_json`` format the engine parses.

Run from backend/:  python scripts/seed.py [--clean]

``--clean`` recreates the schema from scratch (alembic downgrade to base +
upgrade to head) before seeding. Point the target DB with DATABASE_URL.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import sqlalchemy as sa

from core.database import engine
from core.security import hash_password

DEMO_PASSWORD = hash_password("Demo1234!")

# ── Org 1: the original demo tenant ────────────────────────────────────────
USERS = [
    ("admin@crmsplash.mx", "Admin", "admin"),
    ("director@crmsplash.mx", "Director", "director"),
    ("gerente@crmsplash.mx", "Gerente Ventas", "gerente"),
    ("asesor1@crmsplash.mx", "Asesor 1", "asesor"),
    ("asesor2@crmsplash.mx", "Asesor 2", "asesor"),
    ("asesor3@crmsplash.mx", "Asesor 3", "asesor"),
    ("ops@crmsplash.mx", "Operaciones", "operaciones"),
]

# ── Org 2: second tenant (varied roles, for isolation/report demos) ────────
USERS_B = [
    ("admin@norte.mx", "Admin Norte", "admin"),
    ("gerente@norte.mx", "Gerente Norte", "gerente"),
    ("asesor1@norte.mx", "Asesor Norte 1", "asesor"),
    ("asesor2@norte.mx", "Asesor Norte 2", "asesor"),
    ("ops@norte.mx", "Operaciones Norte", "operaciones"),
]

PIPELINE_STAGES = [
    ("Prospección", "Nuevo lead", 0, "#94a3b8", 14, 10),
    ("Contacto Inicial", "Primer contacto", 1, "#60a5fa", 7, 20),
    ("Reunión Agendada", "Reunión programada", 2, "#a78bfa", 14, 30),
    ("Reunión Realizada", "Reunión completada", 3, "#818cf8", 7, 40),
    ("Propuesta Enviada", "Propuesta al cliente", 4, "#f59e0b", 14, 60),
    ("Negociación", "En negociación", 5, "#f97316", 21, 70),
    ("Análisis Documental", "Docs en revisión", 6, "#eab308", 14, 75),
    ("Comité de Crédito", "Evaluación comité", 7, "#ef4444", 14, 80),
    ("Aprobado", "Formalización", 8, "#22c55e", 21, 90),
    ("Cerrado Ganado", "Cliente firmó", 9, "#16a34a", None, 100),
    ("Cerrado Perdido", "Perdida", 10, "#dc2626", None, 0),
    ("Descartado", "Descartada", 11, "#78716c", None, 0),
    ("Standby", "En espera", 12, "#a1a1aa", 30, 50),
]

LOST_REASONS = ["Precio", "No invierte", "Competencia", "Sin respuesta", "No cumple"]
LEAD_SOURCES = ["Referido", "Web", "LinkedIn", "Llamada", "Evento"]

# ── Example automation rules (same format the engine parses) ────────────────
# Each entry: (name, description, trigger_event, conditions, actions)
# conditions: list of {field, op, value}; actions: list of (action_type, config)
AUTOMATION_RULES = [
    (
        "Onboarding al ganar",
        "Al ganar una oportunidad crea una tarea de onboarding en 3 días.",
        "opportunity.won",
        [],
        [
            (
                "create_task",
                {"title": "Onboarding de cliente", "due_offset_days": 3, "assigned_user_id": "__ASESOR__"},
            ),
        ],
    ),
    (
        "Bienvenida al contacto",
        "Al crear un contacto registra una actividad de bienvenida.",
        "contact.created",
        [],
        [
            (
                "create_activity",
                {"type": "note", "subject": "Bienvenida {{ event.full_name }}", "body": "Contacto creado automáticamente."},
            ),
        ],
    ),
    (
        "Seguimiento VIP",
        "Oportunidades de alto valor (estimación > 100,000) reciben tarea de prioridad alta.",
        "opportunity.created",
        [{"field": "value", "op": "gt", "value": 100000}],
        [
            (
                "create_task",
                {"title": "Seguimiento VIP", "priority": "high"},
            ),
        ],
    ),
]


def _insert_org(conn, org_id: str, name: str, slug: str, now: datetime) -> None:
    conn.execute(
        sa.text("INSERT INTO organizations (id, name, slug, created_at, updated_at) VALUES (:i,:n,:s,:t,:t)"),
        {"i": org_id, "n": name, "s": slug, "t": now},
    )


def _hid() -> str:
    """Dash-less uuid4 hex for entities owned by the application domain.

    The ORM defaults for contacts, companies, opportunities, pipelines, stages,
    tasks, activities, lead sources and lost reasons are ``uuid4().hex`` (see
    ``modules/*/domain.py``), and the automation engine/activity subscriber look
    rows up with ``UUID.hex`` (``actions._hex``, ``activities.record_stage_change``).
    Seeding those tables with dashed ids makes every FK from an automation action
    fail and makes every subscriber lookup miss, so the demo data must use the
    same format the app writes. Users and organizations are the exception: their
    domains default to ``str(uuid4())`` (dashed), so they keep ``str(uuid4())``.
    """
    return uuid4().hex


def _insert_users(conn, org_id: str, users: list[tuple[str, str, str]], now: datetime) -> dict[str, str]:
    ids: dict[str, str] = {}
    for email, full_name, role in users:
        uid = str(uuid4())
        ids[role] = uid
        conn.execute(
            sa.text(
                "INSERT INTO users (id, organization_id, email, email_normalized, full_name, "
                "password_hash, role, created_at, updated_at) VALUES (:id,:org,:e,:en,:n,:p,:r,:t,:t)"
            ),
            {"id": uid, "org": org_id, "e": email, "en": email.lower().strip(),
             "n": full_name, "p": DEMO_PASSWORD, "r": role, "t": now},
        )
    return ids


def _insert_lead_sources(conn, org_id: str, now: datetime) -> list[str]:
    ids: list[str] = []
    for src in LEAD_SOURCES:
        sid = _hid()
        ids.append(sid)
        conn.execute(sa.text("INSERT INTO lead_sources (id, organization_id, name, created_at) VALUES (:i,:o,:n,:t)"),
                     {"i": sid, "o": org_id, "n": src, "t": now})
    return ids


def _insert_lost_reasons(conn, org_id: str, now: datetime) -> list[str]:
    ids: list[str] = []
    for reason in LOST_REASONS:
        rid = _hid()
        ids.append(rid)
        conn.execute(sa.text("INSERT INTO lost_reasons (id, organization_id, name, created_at) VALUES (:i,:o,:n,:t)"),
                     {"i": rid, "o": org_id, "n": reason, "t": now})
    return ids


def _insert_pipeline(conn, org_id: str, name: str, now: datetime) -> tuple[str, list[str]]:
    pipe_id = _hid()
    conn.execute(
        sa.text("INSERT INTO pipelines (id, organization_id, name, is_default, created_at, updated_at) VALUES (:i,:o,:n,:dflt,:t,:t)"),
        {"i": pipe_id, "o": org_id, "n": name, "dflt": True, "t": now},
    )
    stage_ids: list[str] = []
    for sname, desc, pos, color, max_d, prob in PIPELINE_STAGES:
        sid = _hid()
        stage_ids.append(sid)
        st = "won" if "Ganado" in sname else "lost" if any(w in sname for w in ("Perdi", "Descarta")) else "open"
        conn.execute(
            sa.text(
                "INSERT INTO pipeline_stages (id, organization_id, pipeline_id, name, description, "
                "position, color, probability, maximum_days, stage_type, created_at, updated_at) "
                "VALUES (:i,:o,:p,:n,:d,:pos,:c,:prob,:md,:st,:t,:t)"
            ),
            {"i": sid, "o": org_id, "p": pipe_id, "n": sname, "d": desc,
             "pos": pos, "c": color, "prob": prob, "md": max_d, "st": st, "t": now},
        )
    return pipe_id, stage_ids


def _insert_companies(conn, org_id: str, count: int, industry: str, now: datetime) -> list[str]:
    ids: list[str] = []
    for i in range(1, count + 1):
        cid = _hid()
        ids.append(cid)
        conn.execute(
            sa.text("INSERT INTO companies (id, organization_id, name, industry, created_at, updated_at) VALUES (:i,:o,:n,:ind,:t,:t)"),
            {"i": cid, "o": org_id, "n": f"Empresa Demo {i}", "ind": industry, "t": now},
        )
    return ids


def _insert_contacts(
    conn, org_id: str, count: int, company_ids: list[str], user_ids: dict[str, str], now: datetime
) -> list[str]:
    ids: list[str] = []
    for i in range(1, count + 1):
        cid = _hid()
        ids.append(cid)
        assigned = user_ids["asesor"] if i <= max(1, count // 2) else user_ids["admin"]
        company = company_ids[i % len(company_ids)] if i <= count - 2 else None
        conn.execute(
            sa.text(
                "INSERT INTO contacts (id, organization_id, company_id, type, first_name, last_name, "
                "email, email_normalized, phone, status, assigned_user_id, created_at, updated_at) "
                "VALUES (:i,:o,:co,'PF',:fn,:ln,:e,:en,:ph,'active',:a,:t,:t)"
            ),
            {"i": cid, "o": org_id, "co": company, "fn": f"Contacto {i}", "ln": f"Apellido {i}",
             "e": f"contacto{i}@demo.mx", "en": f"contacto{i}@demo.mx",
             "ph": f"555000{i:04d}", "a": assigned, "t": now},
        )
    return ids


def _insert_opportunities(
    conn,
    org_id: str,
    count: int,
    contact_ids: list[str],
    company_ids: list[str],
    pipe_id: str,
    stage_ids: list[str],
    source_ids: list[str],
    reason_ids: list[str],
    user_ids: dict[str, str],
    today: date,
    now: datetime,
) -> None:
    for i in range(1, count + 1):
        oid = _hid()
        si = min(i, len(stage_ids) - 1)
        s = stage_ids[si]
        if i <= max(1, count // 4):
            status = "won"; closed_at = now; wv = 50000.0 * i
        elif i <= max(2, count // 2):
            status = "lost"; closed_at = now; wv = None
        else:
            status = "open"; closed_at = None; wv = None

        conn.execute(
            sa.text(
                "INSERT INTO opportunities (id, organization_id, contact_id, company_id, pipeline_id, "
                "stage_id, name, estimated_value, weighted_value, probability, priority, status, "
                "source_id, expected_close_date, closed_at, won_value, lost_reason_id, "
                "assigned_user_id, entered_stage_at, created_at, updated_at) "
                "VALUES (:i,:o,:co,:comp,:p,:s,:n,:ev,:wv,:prob,:pri,:st,:src,:ecd,:ca,:wv2,:lr,:a,:t,:t,:t)"
            ),
            {"i": oid, "o": org_id, "co": contact_ids[i - 1], "comp": company_ids[i % len(company_ids)],
             "p": pipe_id, "s": s, "n": f"Oportunidad Demo {i}",
             "ev": 50000.0 * i, "wv": 50000.0 * i * 0.3, "prob": 30,
             "pri": "medium", "st": status, "src": source_ids[i % len(source_ids)],
             "ecd": today + timedelta(days=30 * i) if status == "open" else today,
             "ca": closed_at, "wv2": wv,
             "lr": reason_ids[i % len(reason_ids)] if status == "lost" else None,
             "a": user_ids["asesor"] if i <= max(1, count // 2) else user_ids["admin"], "t": now},
        )


def _insert_automation_rules(conn, org_id: str, user_ids: dict[str, str], now: datetime) -> int:
    asesor_id = user_ids.get("asesor") or next(iter(user_ids.values()))
    inserted = 0
    for name, description, trigger, conditions, actions in AUTOMATION_RULES:
        rule_id = _hid()
        conn.execute(
            sa.text(
                "INSERT INTO automation_rules (id, organization_id, name, description, trigger_event, "
                "is_active, max_depth, conditions_json, created_at, updated_at) "
                "VALUES (:i,:o,:n,:d,:t,:act,:md,:c,:ts,:ts)"
            ),
            {"i": rule_id, "o": org_id, "n": name, "d": description, "t": trigger,
             "act": True, "md": 5, "c": json.dumps(conditions), "ts": now},
        )
        for position, (action_type, config) in enumerate(actions):
            if "__ASESOR__" in json.dumps(config):
                config = dict(config)
                for k, v in config.items():
                    if v == "__ASESOR__":
                        config[k] = asesor_id
            conn.execute(
                sa.text(
                    "INSERT INTO automation_actions (id, rule_id, action_type, config_json, position) "
                    "VALUES (:i,:r,:a,:c,:p)"
                ),
                {"i": _hid(), "r": rule_id, "a": action_type,
                 "c": json.dumps(config), "p": position},
            )
        inserted += 1
    return inserted


def _seed_org(
    conn,
    *,
    name: str,
    slug: str,
    users: list[tuple[str, str, str]],
    companies: int,
    contacts: int,
    opportunities: int,
    industry: str,
    now: datetime,
    today: date,
) -> dict[str, int]:
    org_id = str(uuid4())
    _insert_org(conn, org_id, name, slug, now)
    user_ids = _insert_users(conn, org_id, users, now)
    source_ids = _insert_lead_sources(conn, org_id, now)
    reason_ids = _insert_lost_reasons(conn, org_id, now)
    pipe_id, stage_ids = _insert_pipeline(conn, org_id, "Pipeline Principal", now)
    company_ids = _insert_companies(conn, org_id, companies, industry, now)
    contact_ids = _insert_contacts(conn, org_id, contacts, company_ids, user_ids, now)
    _insert_opportunities(
        conn, org_id, opportunities, contact_ids, company_ids, pipe_id, stage_ids,
        source_ids, reason_ids, user_ids, today, now,
    )
    rules = _insert_automation_rules(conn, org_id, user_ids, now)
    return {
        "users": len(users), "companies": companies, "contacts": contacts,
        "opportunities": opportunities, "rules": rules,
    }


def _insert_tasks(
    conn, org_id: str, contact_ids: list[str], user_ids: dict[str, str], count: int,
    today: date, now: datetime,
) -> int:
    """Tareas variadas: vencidas, de hoy y futuras (dashboard las agrupa)."""
    statuses = ("pending", "pending", "in_progress", "completed")
    for i in range(1, count + 1):
        st = statuses[i % len(statuses)]
        due = today - timedelta(days=i % 4) if i % 3 == 0 else today + timedelta(days=i)
        conn.execute(
            sa.text(
                "INSERT INTO tasks (id, organization_id, contact_id, assigned_user_id, title, "
                "description, priority, status, due_date, completed_at, created_at, updated_at) "
                "VALUES (:i,:o,:c,:a,:t,:d,:p,:s,:dd,:ca,:t2,:t2)"
            ),
            {"i": _hid(), "o": org_id, "c": contact_ids[i % len(contact_ids)],
             "a": user_ids["asesor"] if i % 2 else user_ids["admin"],
             "t": f"Tarea {i}", "d": f"Seguimiento comercial {i}",
             "p": ("high", "medium", "low")[i % 3], "s": st, "dd": due,
             "ca": now if st == "completed" else None, "t2": now},
        )
    return count


def _insert_activities(
    conn, org_id: str, contact_ids: list[str], user_ids: dict[str, str], count: int,
    now: datetime,
) -> int:
    kinds = ("call", "email", "meeting", "note")
    for i in range(1, count + 1):
        kind = kinds[i % len(kinds)]
        occurred = now - timedelta(hours=i * 5)
        conn.execute(
            sa.text(
                "INSERT INTO activities (id, organization_id, contact_id, user_id, type, subject, "
                "body, occurred_at, duration_minutes, created_at) "
                "VALUES (:i,:o,:c,:u,:t,:s,:b,:oc,:d,:t2)"
            ),
            {"i": _hid(), "o": org_id, "c": contact_ids[i % len(contact_ids)],
             "u": user_ids["asesor"] if i % 2 else user_ids["admin"],
             "t": kind, "s": f"{kind.capitalize()} con contacto {i}",
             "b": "Registro de seguimiento generado por el seed.",
             "oc": occurred, "d": 30, "t2": now},
        )
    return count


def _seed_existing_org(
    conn,
    *,
    slug: str,
    companies: int,
    contacts: int,
    opportunities: int,
    tasks: int,
    activities: int,
    industry: str,
    now: datetime,
    today: date,
) -> dict[str, int] | None:
    """Siembra datos en una org que YA existe (p. ej. la creada en el signup)."""
    row = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = :s"), {"s": slug}
    ).first()
    if row is None:
        print(f"   ✗ org '{slug}' no existe")
        return None
    org_id = row[0]

    users = conn.execute(
        sa.text("SELECT id, role FROM users WHERE organization_id = :o"), {"o": org_id}
    ).fetchall()
    if not users:
        print(f"   ✗ org '{slug}' sin usuarios")
        return None
    admin_id = next((u[0] for u in users if u[1] == "admin"), users[0][0])
    asesor_id = next((u[0] for u in users if u[1] == "asesor"), admin_id)
    user_ids = {"admin": admin_id, "asesor": asesor_id}

    # Idempotente para lead sources / lost reasons: solo si faltan.
    source_ids = [r[0] for r in conn.execute(
        sa.text("SELECT id FROM lead_sources WHERE organization_id = :o"), {"o": org_id})]
    if not source_ids:
        source_ids = _insert_lead_sources(conn, org_id, now)
    reason_ids = [r[0] for r in conn.execute(
        sa.text("SELECT id FROM lost_reasons WHERE organization_id = :o"), {"o": org_id})]
    if not reason_ids:
        reason_ids = _insert_lost_reasons(conn, org_id, now)

    row = conn.execute(
        sa.text("SELECT id FROM pipelines WHERE organization_id = :o AND is_default = :dflt"), {"o": org_id, "dflt": True}
    ).first()
    if row:
        pipe_id = row[0]
        stage_ids = [r[0] for r in conn.execute(
            sa.text("SELECT id FROM pipeline_stages WHERE pipeline_id = :p ORDER BY position"),
            {"p": pipe_id})]
    else:
        pipe_id, stage_ids = _insert_pipeline(conn, org_id, "Pipeline Principal", now)

    company_ids = _insert_companies(conn, org_id, companies, industry, now)
    contact_ids = _insert_contacts(conn, org_id, contacts, company_ids, user_ids, now)
    _insert_opportunities(
        conn, org_id, opportunities, contact_ids, company_ids, pipe_id, stage_ids,
        source_ids, reason_ids, user_ids, today, now,
    )
    _insert_tasks(conn, org_id, contact_ids, user_ids, tasks, today, now)
    _insert_activities(conn, org_id, contact_ids, user_ids, activities, now)
    rules = _insert_automation_rules(conn, org_id, user_ids, now)
    return {
        "users": len(users), "companies": companies, "contacts": contacts,
        "opportunities": opportunities, "tasks": tasks, "activities": activities,
        "rules": rules,
    }


def _clean_db() -> None:
    """Drop every table (downgrade to base) and re-apply migrations."""
    from alembic import command
    from alembic.config import Config

    from core.config import get_settings

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    try:
        command.downgrade(cfg, "base")
    except Exception:  # noqa: BLE001 — fresh DB without alembic_version
        print("   (sin schema previo — DB limpia)")
    command.upgrade(cfg, "head")


def seed(only_slug: str | None = None) -> None:
    now = datetime.now(UTC)
    today = now.date()

    if only_slug:
        with engine.begin() as conn:
            counts = _seed_existing_org(
                conn, slug=only_slug, companies=10, contacts=30, opportunities=20,
                tasks=12, activities=15, industry="Servicios Financieros",
                now=now, today=today,
            )
        if counts:
            print(f"✅ Org '{only_slug}' sembrada: {counts}")
        return

    orgs = [
        {"name": "CRM Splash Demo", "slug": "crm-splash-demo", "users": USERS,
         "companies": 10, "contacts": 30, "opportunities": 20, "industry": "Servicios Financieros"},
        {"name": "CRM Splash Norte", "slug": "crm-splash-norte", "users": USERS_B,
         "companies": 5, "contacts": 12, "opportunities": 8, "industry": "Manufactura"},
    ]

    total_rules = 0
    with engine.begin() as conn:
        for org in orgs:
            counts = _seed_org(conn, now=now, today=today, **org)
            total_rules += counts["rules"]
            print(f"   • {org['name']} ({org['slug']}): {counts['users']} usuarios · "
                  f"{counts['companies']} empresas · {counts['contacts']} contactos · "
                  f"{counts['opportunities']} oportunidades · {counts['rules']} reglas")

    print("✅ Seed completado:")
    print(f"   2 organizaciones  ·  {total_rules} reglas de automatización")
    print("\n   🔑 Password para todos: Demo1234!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed CRM-Splash demo data (2 orgs).")
    parser.add_argument("--clean", action="store_true", help="recreate the schema from scratch before seeding")
    parser.add_argument("--org", metavar="SLUG", help="seed an EXISTING org (e.g. the one from signup)")
    args = parser.parse_args()
    if args.clean:
        print("♻️  Recreando schema (alembic downgrade base → upgrade head)…")
        _clean_db()
    seed(only_slug=args.org)

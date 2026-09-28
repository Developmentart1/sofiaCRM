"""Initial migration — creates every table in dependency order.

Revision ID: 0001_initial
Revises: None
Create Date: 2026-08-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Organizations ──────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Mexico_City"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MXN"),
        sa.Column("locale", sa.String(8), nullable=False, server_default="es-MX"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # ── Users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("email_normalized", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="asesor"),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email_normalized", "users", ["email_normalized"])
    op.create_index("ix_user_org_role", "users", ["organization_id", "role"])

    # ── Companies ──────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("legal_name", sa.String(300), nullable=True),
        sa.Column("rfc", sa.String(13), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("address_street", sa.String(300), nullable=True),
        sa.Column("address_city", sa.String(100), nullable=True),
        sa.Column("address_state", sa.String(100), nullable=True),
        sa.Column("address_zip", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_companies_organization_id", "companies", ["organization_id"])

    # ── Contacts (PF = Persona Física, PM = Persona Moral) ─────────
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(2), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=True),
        sa.Column("legal_name", sa.String(300), nullable=True),
        sa.Column("rfc", sa.String(13), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("email_normalized", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("phone_normalized", sa.String(20), nullable=True),
        sa.Column("mobile", sa.String(30), nullable=True),
        sa.Column("position", sa.String(200), nullable=True),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("address_street", sa.String(300), nullable=True),
        sa.Column("address_city", sa.String(100), nullable=True),
        sa.Column("address_state", sa.String(100), nullable=True),
        sa.Column("address_zip", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_contacts_organization_id", "contacts", ["organization_id"])
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_contacts_email_normalized", "contacts", ["email_normalized"])
    op.create_index("ix_contacts_phone_normalized", "contacts", ["phone_normalized"])
    op.create_index("ix_contacts_assigned_user_id", "contacts", ["assigned_user_id"])

    # ── Lead Sources ───────────────────────────────────────────────
    op.create_table(
        "lead_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lead_sources_organization_id", "lead_sources", ["organization_id"])

    # ── Pipelines ──────────────────────────────────────────────────
    op.create_table(
        "pipelines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(20), nullable=False, server_default="opportunity"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pipelines_organization_id", "pipelines", ["organization_id"])

    # ── Pipeline Stages ────────────────────────────────────────────
    op.create_table(
        "pipeline_stages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(9), nullable=True),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maximum_days", sa.Integer(), nullable=True),
        sa.Column("stage_type", sa.String(20), nullable=False, server_default="open"),
        sa.Column("entry_requirements", sa.Text(), nullable=True),
        sa.Column("exit_requirements", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pipeline_stages_organization_id", "pipeline_stages", ["organization_id"])
    op.create_index("ix_pipeline_stages_pipeline_id", "pipeline_stages", ["pipeline_id"])

    # ── Opportunities ──────────────────────────────────────────────
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pipeline_id", sa.String(36), sa.ForeignKey("pipelines.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stage_id", sa.String(36), sa.ForeignKey("pipeline_stages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MXN"),
        sa.Column("estimated_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("weighted_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("probability", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("lead_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("won_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("lost_reason_id", sa.String(36), nullable=True),
        sa.Column("lost_notes", sa.Text(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
        sa.Column("next_activity_at", sa.DateTime(), nullable=True),
        sa.Column("entered_stage_at", sa.DateTime(), nullable=True),
        sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_opportunities_organization_id", "opportunities", ["organization_id"])
    op.create_index("ix_opportunities_contact_id", "opportunities", ["contact_id"])
    op.create_index("ix_opportunities_company_id", "opportunities", ["company_id"])
    op.create_index("ix_opportunities_pipeline_id", "opportunities", ["pipeline_id"])
    op.create_index("ix_opportunities_stage_id", "opportunities", ["stage_id"])
    op.create_index("ix_opportunities_assigned_user_id", "opportunities", ["assigned_user_id"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])

    # ── Lost Reasons ───────────────────────────────────────────────
    op.create_table(
        "lost_reasons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lost_reasons_organization_id", "lost_reasons", ["organization_id"])

    # ── Activities ─────────────────────────────────────────────────
    op.create_table(
        "activities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_activities_organization_id", "activities", ["organization_id"])
    op.create_index("ix_activities_contact_id", "activities", ["contact_id"])
    op.create_index("ix_activities_opportunity_id", "activities", ["opportunity_id"])
    op.create_index("ix_activities_user_id", "activities", ["user_id"])

    # ── Tasks ──────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_time", sa.Time(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tasks_organization_id", "tasks", ["organization_id"])
    op.create_index("ix_tasks_assigned_user_id", "tasks", ["assigned_user_id"])
    op.create_index("ix_tasks_opportunity_id", "tasks", ["opportunity_id"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # ── Documents ──────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("safe_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_contact_id", "documents", ["contact_id"])

    # ── Audit Logs ─────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_entity_type_id", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── Event Outbox ───────────────────────────────────────────────
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_event_outbox_dispatched", "event_outbox", ["dispatched_at"])
    op.create_index("ix_event_outbox_organization_id", "event_outbox", ["organization_id"])

    # ── Automation Rules ───────────────────────────────────────────
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_event", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_automation_rules_organization_id", "automation_rules", ["organization_id"])

    # ── Automation Actions ─────────────────────────────────────────
    op.create_table(
        "automation_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── Automation Executions ──────────────────────────────────────
    op.create_table(
        "automation_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_event_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )

    # ── Custom Field Definitions ───────────────────────────────────
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(30), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_custom_field_defs_org_entity", "custom_field_definitions", ["organization_id", "entity_type"])

    # ── Custom Field Values ────────────────────────────────────────
    op.create_table(
        "custom_field_values",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("definition_id", sa.String(36), sa.ForeignKey("custom_field_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(18, 4), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("value_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_custom_field_values_def_entity", "custom_field_values", ["definition_id", "entity_id"], unique=True)

    # ── Notifications ──────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_notifications_user_id_read", "notifications", ["user_id", "is_read"])
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])


def downgrade() -> None:
    tables = [
        "notifications", "custom_field_values", "custom_field_definitions",
        "automation_executions", "automation_actions", "automation_rules",
        "event_outbox", "audit_logs", "documents", "tasks", "activities",
        "lost_reasons", "opportunities", "pipeline_stages", "pipelines",
        "lead_sources", "contacts", "companies", "users", "organizations",
    ]
    for t in tables:
        op.drop_table(t)

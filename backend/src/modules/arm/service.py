"""ARM service - synchronous LLM-assisted relation management."""

from sqlalchemy.orm import Session

from core.errors import CRMError, NotFoundError
from core.tenant import current_org_id
from modules.activities.domain import Activity
from modules.contacts.domain import Contact

from . import llm
from .llm import ArmLLMError

_RECENT_ACTIVITY_LIMIT = 20


def _contact_name(contact: Contact) -> str:
    return " ".join(part for part in (contact.first_name, contact.last_name) if part).strip()


class ArmService:
    def __init__(self, db: Session):
        self.db = db

    def _get_contact(self, contact_id: str) -> Contact:
        org = current_org_id()
        contact = (
            self.db.query(Contact)
            .filter(
                Contact.id == contact_id,
                Contact.organization_id == org,
                Contact.deleted_at.is_(None),
            )
            .first()
        )
        if not contact:
            raise NotFoundError(f"contact {contact_id} not found")
        return contact

    def _recent_activities(self, contact_id: str) -> list[Activity]:
        org = current_org_id()
        return (
            self.db.query(Activity)
            .filter(
                Activity.organization_id == org,
                Activity.contact_id == contact_id,
            )
            .order_by(Activity.occurred_at.desc(), Activity.created_at.desc())
            .limit(_RECENT_ACTIVITY_LIMIT)
            .all()
        )

    @staticmethod
    def _activity_lines(activities: list[Activity]) -> list[str]:
        lines: list[str] = []
        for activity in activities:
            when = activity.occurred_at or activity.created_at
            when_text = when.isoformat() if when else "unknown"
            parts = [f"- [{activity.type}] {when_text}"]
            if activity.subject:
                parts.append(f"subject: {activity.subject}")
            if activity.body:
                parts.append(f"body: {activity.body}")
            lines.append(" ".join(parts))
        return lines

    def _complete(self, system: str, user: str) -> str:
        try:
            return llm.complete(system, user)
        except CRMError:
            raise
        except Exception as exc:
            raise ArmLLMError("LLM call failed", details={"reason": str(exc)}) from exc

    def draft_followup(self, contact_id: str) -> str:
        contact = self._get_contact(contact_id)
        activities = self._recent_activities(contact_id)
        activities_text = "\n".join(self._activity_lines(activities)) or "(sin actividades recientes)"

        system = (
            "Eres un asistente de CRM. Redacta un mensaje de seguimiento breve, "
            "profesional y en espanol, usando unicamente los datos proporcionados."
        )
        user = (
            f"Contacto: {_contact_name(contact)}\n"
            f"Actividades recientes:\n{activities_text}\n\n"
            "Redacta el mensaje de seguimiento:"
        )
        return self._complete(system, user)

    def summarize_relation(self, contact_id: str) -> str:
        contact = self._get_contact(contact_id)
        activities = self._recent_activities(contact_id)
        activities_text = "\n".join(self._activity_lines(activities)) or "(sin actividades recientes)"

        system = (
            "Eres un asistente de CRM. Resume la relacion con el contacto "
            "usando unicamente los datos proporcionados, en espanol."
        )
        user = (
            f"Contacto: {_contact_name(contact)}\n"
            f"Actividades recientes:\n{activities_text}\n\n"
            "Resume la relacion:"
        )
        return self._complete(system, user)

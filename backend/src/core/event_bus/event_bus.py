"""Synchronous event bus with SQLite outbox persistence.

API:
    bus = SyncEventBus()
    bus.subscribe("opportunity.won", handler)
    bus.publish(event, db=session)   # writes to outbox in the same TX
    bus.dispatch_pending(db=session) # delivers to subscribers

The ``EventOutbox`` ORM model mirrors the ``event_outbox`` table created by
migration ``0001_initial`` (columns: aggregate_id, occurred_at, retries, error).
"""

import json
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

from ..database import Base
from .models import BaseEvent, EventEnvelope

log = logging.getLogger(__name__)


# --- Outbox table ---

class EventOutbox(Base):
    """Outbox row. Written transactionally with the originating state change."""

    __tablename__ = "event_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(36), nullable=False)
    payload_json = Column(Text, nullable=False)
    occurred_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    dispatched_at = Column(DateTime, nullable=True, index=True)
    retries = Column(Integer, default=0, nullable=False)
    error = Column(Text, nullable=True)


# --- Handler type ---

EventHandler = Callable[[BaseEvent, Session], None]

_AGGREGATE_ID_FIELDS = (
    "contact_id",
    "company_id",
    "opportunity_id",
    "pipeline_id",
    "stage_id",
    "task_id",
    "activity_id",
    "document_id",
    "winner_id",
)


def _event_aggregate_id(event: BaseEvent) -> str:
    """Best-effort aggregate id for the outbox row (falls back to org id)."""
    for field in _AGGREGATE_ID_FIELDS:
        value = getattr(event, field, None)
        if value is not None:
            return str(value)
    return str(event.organization_id)


class SyncEventBus:
    """In-process bus. Subscribers are matched by event_type string."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def subscribe_event(self, event_cls: type[BaseEvent], handler: EventHandler) -> None:
        """Subscribe using the Pydantic class — extract event_type literal."""
        self._subscribers[event_cls.model_fields["event_type"].default].append(handler)

    def publish(
        self,
        event: BaseEvent,
        *,
        db: Session,
    ) -> str:
        """Persist the event to the outbox inside the caller's transaction.

        Handlers are delivered **synchronously** (within the caller's
        transaction) so side effects (e.g. the ``stage_change`` activity) are
        guaranteed to be committed atomically with the originating change.
        The outbox row is marked dispatched so the background loop skips it.
        """
        row = EventOutbox(
            id=str(uuid4()),
            organization_id=str(event.organization_id),
            event_type=event.event_type,
            aggregate_id=_event_aggregate_id(event),
            payload_json=event.model_dump_json(),
        )
        db.add(row)
        db.flush()
        log.debug("event_outbox.persisted id=%s type=%s", row.id, row.event_type)
        self._deliver(row, event, db)
        return row.id

    def _deliver(self, row: "EventOutbox", event: BaseEvent, db: Session) -> None:
        """Deliver one event to its subscribers, tracking outcome on the row.

        On success the row is marked dispatched (so it is not re-delivered).
        On failure ``dispatched_at`` stays NULL and the error is recorded so
        the background loop can retry, matching the pre-existing semantics.
        """
        failed = False
        for handler in list(self._subscribers.get(row.event_type, [])):
            try:
                handler(event, db)
            except Exception as exc:  # noqa: BLE001
                failed = True
                row.retries += 1
                row.error = repr(exc)[:2000]
                log.exception("event_bus.handler_failed id=%s type=%s", row.id, row.event_type)
        if not failed:
            row.dispatched_at = datetime.now(UTC)
            row.retries += 1
        db.flush()

    def dispatch_pending(self, *, db: Session, limit: int = 100) -> int:
        """Deliver all undelivered outbox rows to subscribers.

        Idempotent per row: once dispatched_at is set, the row is skipped.
        Failed handlers bump retries and store the error for retry.
        """
        rows = (
            db.query(EventOutbox)
            .filter(EventOutbox.dispatched_at.is_(None))
            .order_by(EventOutbox.occurred_at.asc())
            .limit(limit)
            .all()
        )
        delivered = 0
        for row in rows:
            try:
                payload = json.loads(row.payload_json)
                # Re-hydrate via Pydantic discriminated union so handlers
                # receive the right concrete subclass.
                event = _parse_event(payload)
            except Exception as exc:  # noqa: BLE001
                row.retries += 1
                row.error = repr(exc)[:2000]
                log.exception("event_bus.parse_failed id=%s", row.id)
                continue
            self._deliver(row, event, db)
            delivered += 1
        db.flush()
        return delivered


# --- Singleton wiring ---

_bus: SyncEventBus | None = None


def configure_bus() -> SyncEventBus:
    """Create and cache the singleton bus. Called at app startup."""
    global _bus
    if _bus is None:
        _bus = SyncEventBus()
    return _bus


def get_bus() -> SyncEventBus:
    """Return the configured bus; lazily configure if needed."""
    if _bus is None:
        return configure_bus()
    return _bus


def _parse_event(payload: dict[str, Any]) -> BaseEvent:
    """Re-hydrate an event payload into the right Pydantic subclass."""
    # Pydantic discriminated union: pick by event_type
    from pydantic import TypeAdapter

    adapter: TypeAdapter[EventEnvelope] = TypeAdapter(EventEnvelope)
    return adapter.validate_python(payload)

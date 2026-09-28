"""Condition evaluation for automation rules.

``conditions_json`` on a rule is a JSON array of ``{field, op, value}`` objects
combined with AND. Supported operators: ``eq``, ``neq``, ``contains``, ``gt``,
``lt``. ``field`` resolves against the event payload's attributes (flat, one
level — e.g. ``to_stage_id``). A rule with no conditions always matches.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from core.event_bus.models import BaseEvent

OPS = frozenset({"eq", "neq", "contains", "gt", "lt"})


def _comparable(value: Any) -> Any:
    """Normalise an event value so it can be compared against a JSON scalar."""
    if isinstance(value, UUID):
        # Stored entity ids are dash-less hex; stringify UUIDs the same way so
        # e.g. ``to_stage_id eq <hex>`` matches.
        return value.hex
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _event_field(event: BaseEvent, field: str) -> Any:
    return _comparable(getattr(event, field, None))


def _coerce_numeric(actual: Any, expected: Any) -> tuple[float | None, float | None]:
    try:
        return float(actual), float(expected)
    except (TypeError, ValueError):
        return None, None


def _compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return str(actual) == str(expected)
    if op == "neq":
        return str(actual) != str(expected)
    if op == "contains":
        if actual is None:
            return False
        return str(expected) in str(actual)

    # gt / lt
    if actual is None:
        return False
    a_num, e_num = _coerce_numeric(actual, expected)
    if a_num is not None and e_num is not None:
        return a_num > e_num if op == "gt" else a_num < e_num
    return str(actual) > str(expected) if op == "gt" else str(actual) < str(expected)


def evaluate_conditions(conditions: list[dict[str, Any]] | None, event: BaseEvent) -> bool:
    """Return True iff every condition matches (AND semantics)."""
    if not conditions:
        return True
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("op", "eq")
        expected = cond.get("value")
        if op not in OPS:
            return False
        actual = _event_field(event, field)
        if not _compare(actual, op, expected):
            return False
    return True

"""Normalisation helpers for email and phone used in duplicate detection."""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"\D+")


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip().lower()
    if not v:
        return None
    if not _EMAIL_RE.match(v):
        return v  # keep but let downstream validators complain
    return v


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    digits = _PHONE_RE.sub("", value)
    if not digits:
        return None
    # Mexican default: keep last 10 digits
    if len(digits) >= 10:
        digits = digits[-10:]
    return digits


def normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    v = " ".join(value.strip().lower().split())
    return v or None

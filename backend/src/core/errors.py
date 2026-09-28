"""Typed application errors. All inherit from CRMError for clean exception handlers."""

from typing import Any


class CRMError(Exception):
    """Base application error. Maps to a JSON response with status_code."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnauthorizedError(CRMError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(CRMError):
    status_code = 403
    code = "forbidden"


class NotFoundError(CRMError):
    status_code = 404
    code = "not_found"


class ConflictError(CRMError):
    status_code = 409
    code = "conflict"


class ValidationError(CRMError):
    status_code = 422
    code = "validation_error"


class StageTransitionError(CRMError):
    status_code = 422
    code = "stage_transition_error"


class MissingRequiredFieldError(CRMError):
    status_code = 422
    code = "missing_required_field"


class OrganizationBoundaryError(CRMError):
    """Raised when an operation crosses the org isolation boundary."""

    status_code = 403
    code = "organization_boundary"

class DomainError(Exception):
    """Base for business-rule violations; mapped to HTTP 4xx by the API layer."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, *, rule: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.rule = rule


class NotFound(DomainError):
    status_code = 404
    code = "not_found"


class PermissionDenied(DomainError):
    status_code = 403
    code = "permission_denied"


class SeparationOfDutiesViolation(PermissionDenied):
    code = "separation_of_duties"


class InvalidTransition(DomainError):
    status_code = 409
    code = "invalid_transition"


class ReasonRequired(DomainError):
    status_code = 422
    code = "reason_required"


class IntegrityFailure(DomainError):
    status_code = 500
    code = "integrity_failure"

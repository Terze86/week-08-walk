"""Who may do what in casework. Kept together so the laboratory can review it.

Open questions for the laboratory are marked CONFIRM.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import access
from app.core.access import AccessGrant, GrantKind
from app.core.errors import NotFound, PermissionDenied
from app.modules.identity.models import Role, User

# Roles that work on casework records at all. CODIS Scientists see only what is
# shared with them (WF-01.06); LIMS Admins see audit history, not casework.
CASEWORK_ROLES = frozenset(
    {Role.CASE_SCIENTIST, Role.SCREENING_LAB_OFFICER, Role.DNA_LAB_OFFICER, Role.REVIEWER}
)
# CONFIRM: who registers cases, checks exhibits and signs receipts.
RECEPTION_ROLES = frozenset({Role.CASE_SCIENTIST, Role.SCREENING_LAB_OFFICER})
# CONFIRM: who assigns Case Scientists to subcases (WF-03.01).
ASSIGNER_ROLES = frozenset({Role.CASE_SCIENTIST, Role.REVIEWER})
# Who handles physical items (WF-03.04).
CUSTODY_ROLES = CASEWORK_ROLES
# CONFIRM: who may authorise a custody correction (WF-03.10).
CORRECTION_AUTHORIZER_ROLES = frozenset({Role.CASE_SCIENTIST, Role.REVIEWER})

SUBCASE = "subcase"
EXHIBIT_EXAMINATION = "exhibit_examination"


def require_roles(user: User, roles: frozenset[Role], what: str) -> None:
    if not user.is_active:
        raise PermissionDenied("Account is disabled")
    if not user.roles & roles:
        raise PermissionDenied(f"You are not permitted to {what}")


def require_lab(user: User, laboratory_id: uuid.UUID) -> None:
    """Casework staff see the records of their own laboratories (WF-01.05).
    Out-of-lab records are reported as not found, so their existence is not leaked."""
    if not user.roles & CASEWORK_ROLES or laboratory_id not in user.laboratory_ids:
        raise NotFound("Record not found")


def assignee_ids(session: Session, entity_type: str, entity_id: object) -> set[uuid.UUID]:
    return set(
        session.execute(
            select(AccessGrant.user_id).where(
                AccessGrant.entity_type == entity_type,
                AccessGrant.entity_id == str(entity_id),
                AccessGrant.kind == GrantKind.ASSIGNMENT,
                AccessGrant.revoked_at.is_(None),
            )
        ).scalars()
    )


def is_assigned(session: Session, user: User, entity_type: str, entity_id: object) -> bool:
    return access.has_grant(session, user.id, entity_type, entity_id, kinds=(GrantKind.ASSIGNMENT,))

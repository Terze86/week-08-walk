"""Separation-of-duties rules, kept in one place so they can be reviewed and
validated as a set. Each rule cites the workflow steps (docs/URS.md) it enforces.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from app.core.errors import SeparationOfDutiesViolation
from app.modules.identity.models import SCIENTIFIC_ROLES, Role, User


@dataclass(frozen=True)
class SodRule:
    id: str
    description: str
    urs: tuple[str, ...]


INDEPENDENT_PROFILE_READERS = SodRule(
    "SOD-READERS",
    "The two independent profile readings must be made by different Case Scientists.",
    ("WF-01.04", "WF-11.01"),
)
INDEPENDENT_EXTRACTION_CHECK = SodRule(
    "SOD-EXTRACTION-CHECK",
    "The extraction setup check must be made by a different DNA Lab Officer than the loader.",
    ("WF-07.07",),
)
HANDOVER_RECEIVER_ACCEPTS = SodRule(
    "SOD-HANDOVER",
    "Only the designated receiving person may accept a person-to-person handover.",
    ("WF-03.08",),
)
FINAL_SIGNOFF_TECH_REVIEWER = SodRule(
    "SOD-FINAL-SIGNOFF",
    "Final report sign-off is performed by the assigned technical Reviewer.",
    ("WF-17.07",),
)
ADMIN_NO_SCIENTIFIC_DECISIONS = SodRule(
    "SOD-ADMIN",
    "LIMS Admin access may not be used to make or alter scientific decisions.",
    ("WF-19.04",),
)
CODIS_SHARED_ONLY = SodRule(
    "SOD-CODIS-SCOPE",
    "CODIS Scientists see only the requests, profiles and files shared with them.",
    ("WF-01.06", "WF-14.03", "WF-15.03"),
)

ALL_RULES: tuple[SodRule, ...] = (
    INDEPENDENT_PROFILE_READERS,
    INDEPENDENT_EXTRACTION_CHECK,
    HANDOVER_RECEIVER_ACCEPTS,
    FINAL_SIGNOFF_TECH_REVIEWER,
    ADMIN_NO_SCIENTIFIC_DECISIONS,
    CODIS_SHARED_ONLY,
)


def require_different_people(rule: SodRule, people: Iterable[uuid.UUID | None]) -> None:
    ids = [p for p in people if p is not None]
    if len(ids) != len(set(ids)):
        raise SeparationOfDutiesViolation(rule.description, rule=rule.id)


def require_designated_person(rule: SodRule, actor: User, designated: uuid.UUID | None) -> None:
    if designated is None or actor.id != designated:
        raise SeparationOfDutiesViolation(rule.description, rule=rule.id)


def require_scientific_role(rule: SodRule, actor: User, *roles: Role) -> None:
    """The actor must hold a scientific role for this action; admin rights never suffice."""
    wanted = set(roles) or set(SCIENTIFIC_ROLES)
    if not actor.roles & wanted & SCIENTIFIC_ROLES:
        raise SeparationOfDutiesViolation(rule.description, rule=rule.id)

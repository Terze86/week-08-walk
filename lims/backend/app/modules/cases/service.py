"""Case registration, subcases, exhibits and assignments (WF-02.01 to WF-02.06,
WF-03.01 to WF-03.03)."""

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import access, audit
from app.core.access import AccessGrant, GrantKind
from app.core.errors import DomainError, InvalidTransition, NotFound, PermissionDenied
from app.core.ids import next_identifier
from app.core.workflow import GuardContext, StateMachine, Transition
from app.modules.cases import policy
from app.modules.cases.models import (
    Case,
    Exhibit,
    ExhibitState,
    Subcase,
    SubcaseState,
    SubmissionSource,
)
from app.modules.identity.models import Laboratory, Role, User
from app.modules.items.models import Item, ItemKind
from app.modules.reference.models import Client

# --- Exhibit state machine -------------------------------------------------


def _check_recorded(ctx: GuardContext) -> None:
    """Accepting needs the three receipt checks recorded (WF-02.05); any
    discrepancy must be explained."""
    checks = [ctx.data.get(k) for k in ("description_matches", "marking_matches", "seal_intact")]
    if any(c is None for c in checks):
        raise DomainError("Record the description, marking and seal checks before accepting")
    if not all(checks) and not ctx.reason:
        raise DomainError("Explain the discrepancy found during the check")


def _not_on_open_receipt(ctx: GuardContext) -> None:
    from app.modules.receipt.service import open_receipt_for

    if open_receipt_for(ctx.session, ctx.entity.id) is not None:
        raise InvalidTransition("Cancel the draft receipt that lists this exhibit first")


EXHIBIT_MACHINE = StateMachine.build(
    "exhibit",
    states=[s.value for s in ExhibitState],
    initial=ExhibitState.SUBMITTED.value,
    transitions=[
        Transition(
            "accept",
            frozenset({ExhibitState.SUBMITTED}),
            ExhibitState.ACCEPTED,
            policy.RECEPTION_ROLES,
            guards=(_check_recorded,),
        ),
        Transition(
            "reject",
            frozenset({ExhibitState.SUBMITTED}),
            ExhibitState.REJECTED,
            policy.RECEPTION_ROLES,
            reason_required=True,
        ),
        Transition(
            "reconsider",
            frozenset({ExhibitState.ACCEPTED, ExhibitState.REJECTED}),
            ExhibitState.SUBMITTED,
            policy.RECEPTION_ROLES,
            reason_required=True,
            guards=(_not_on_open_receipt,),
        ),
        Transition(
            "receive",
            frozenset({ExhibitState.ACCEPTED}),
            ExhibitState.RECEIVED,
            policy.RECEPTION_ROLES,
        ),
    ],
)


# --- Lookups ---------------------------------------------------------------


def get_case(session: Session, user: User, case_id: uuid.UUID) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise NotFound("Record not found")
    policy.require_lab(user, case.laboratory_id)
    return case


def get_subcase(session: Session, user: User, subcase_id: uuid.UUID) -> Subcase:
    subcase = session.get(Subcase, subcase_id)
    if subcase is None:
        raise NotFound("Record not found")
    policy.require_lab(user, subcase.laboratory_id)
    return subcase


def get_exhibit(session: Session, user: User, exhibit_id: uuid.UUID) -> Exhibit:
    exhibit = session.get(Exhibit, exhibit_id)
    if exhibit is None:
        raise NotFound("Record not found")
    get_subcase(session, user, exhibit.subcase_id)
    return exhibit


def _open_subcase(session: Session, user: User, subcase_id: uuid.UUID) -> Subcase:
    subcase = get_subcase(session, user, subcase_id)
    if subcase.state != SubcaseState.OPEN:
        raise InvalidTransition("The laboratory subcase is closed")
    return subcase


# --- Registration ----------------------------------------------------------

CASE_DETAIL_FIELDS = (
    "client_reference",
    "submission_reference",
    "submitter_name",
    "submitter_contact",
    "investigating_officer_name",
    "investigating_officer_contact",
    "case_information",
)


def register_case(
    session: Session,
    *,
    actor: User,
    laboratory_id: uuid.UUID,
    client_id: uuid.UUID,
    client_reference: str,
    source: SubmissionSource,
    submitter_name: str,
    investigating_officer_name: str,
    submission_reference: str | None = None,
    submitter_contact: str | None = None,
    investigating_officer_contact: str | None = None,
    case_information: str | None = None,
) -> tuple[Case, Subcase]:
    """Register a case and open its first laboratory subcase."""
    policy.require_roles(actor, policy.RECEPTION_ROLES, "register cases")
    if session.get(Laboratory, laboratory_id) is None:
        raise NotFound("Laboratory not found")
    policy.require_lab(actor, laboratory_id)
    client = session.get(Client, client_id)
    if client is None or not client.active:
        raise NotFound("Client not found")
    if source == SubmissionSource.ELECTRONIC and not submission_reference:
        raise DomainError("An electronic submission needs its submission reference")

    case = Case(
        case_number=next_identifier(session, "case"),
        laboratory_id=laboratory_id,
        client_id=client_id,
        client_reference=client_reference,
        source=source,
        submission_reference=submission_reference,
        submitter_name=submitter_name,
        submitter_contact=submitter_contact,
        investigating_officer_name=investigating_officer_name,
        investigating_officer_contact=investigating_officer_contact,
        case_information=case_information,
        registered_by=actor.id,
    )
    session.add(case)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="case.registered",
        entity_type="case",
        entity_id=case.id,
        after={"case_number": case.case_number, "client_id": str(client_id), "source": source}
        | {f: getattr(case, f) for f in CASE_DETAIL_FIELDS},
    )
    return case, create_subcase(session, actor=actor, case_id=case.id)


def create_subcase(session: Session, *, actor: User, case_id: uuid.UUID) -> Subcase:
    policy.require_roles(actor, policy.RECEPTION_ROLES, "create laboratory subcases")
    case = get_case(session, actor, case_id)
    subcase = Subcase(
        subcase_number=next_identifier(session, "subcase"),
        case_id=case.id,
        laboratory_id=case.laboratory_id,
        created_by=actor.id,
    )
    session.add(subcase)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="subcase.created",
        entity_type="subcase",
        entity_id=subcase.id,
        after={"subcase_number": subcase.subcase_number, "case_id": str(case.id)},
    )
    return subcase


def update_case_details(
    session: Session, *, actor: User, case_id: uuid.UUID, changes: dict[str, Any], reason: str
) -> Case:
    policy.require_roles(actor, policy.RECEPTION_ROLES, "change case details")
    case = get_case(session, actor, case_id)
    unknown = set(changes) - set(CASE_DETAIL_FIELDS)
    if unknown:
        raise DomainError(f"These fields cannot be changed here: {sorted(unknown)}")
    before = {f: getattr(case, f) for f in changes}
    changed = {f: v for f, v in changes.items() if before[f] != v}
    if not changed:
        raise DomainError("Nothing to change")
    for field, value in changed.items():
        setattr(case, field, value)
    audit.record(
        session,
        actor_id=actor.id,
        action="case.details_corrected",
        entity_type="case",
        entity_id=case.id,
        reason=reason,
        before={f: before[f] for f in changed},
        after=changed,
    )
    return case


# --- Exhibits --------------------------------------------------------------


def add_exhibit(
    session: Session,
    *,
    actor: User,
    subcase_id: uuid.UUID,
    description: str,
    marking: str | None = None,
    seal: str | None = None,
    submitter_item_ref: str | None = None,
) -> Exhibit:
    """Record an exhibit listed on the submission and give it an identifier and
    barcode (WF-02.03, WF-02.04)."""
    policy.require_roles(actor, policy.RECEPTION_ROLES, "record exhibits")
    subcase = _open_subcase(session, actor, subcase_id)
    barcode = next_identifier(session, "exhibit")
    item = Item(barcode=barcode, kind=ItemKind.EXHIBIT, subcase_id=subcase.id, label=description)
    session.add(item)
    session.flush()
    exhibit = Exhibit(
        id=item.id,
        subcase_id=subcase.id,
        submitter_item_ref=submitter_item_ref,
        description=description,
        marking=marking,
        seal=seal,
        state=ExhibitState.SUBMITTED,
        recorded_by=actor.id,
    )
    session.add(exhibit)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="exhibit.recorded",
        entity_type="exhibit",
        entity_id=exhibit.id,
        after={
            "barcode": barcode,
            "subcase_id": str(subcase.id),
            "description": description,
            "marking": marking,
            "seal": seal,
            "submitter_item_ref": submitter_item_ref,
        },
    )
    return exhibit


def accept_exhibit(
    session: Session,
    *,
    actor: User,
    exhibit_id: uuid.UUID,
    description_matches: bool,
    marking_matches: bool,
    seal_intact: bool,
    notes: str | None = None,
) -> Exhibit:
    exhibit = get_exhibit(session, actor, exhibit_id)
    _open_subcase(session, actor, exhibit.subcase_id)
    checks = {
        "description_matches": description_matches,
        "marking_matches": marking_matches,
        "seal_intact": seal_intact,
    }
    EXHIBIT_MACHINE.apply(session, exhibit, "accept", actor=actor, reason=notes, data=checks)
    _store_check(exhibit, actor, checks, notes)
    return exhibit


def reject_exhibit(
    session: Session,
    *,
    actor: User,
    exhibit_id: uuid.UUID,
    reason: str,
    description_matches: bool | None = None,
    marking_matches: bool | None = None,
    seal_intact: bool | None = None,
) -> Exhibit:
    exhibit = get_exhibit(session, actor, exhibit_id)
    _open_subcase(session, actor, exhibit.subcase_id)
    checks = {
        "description_matches": description_matches,
        "marking_matches": marking_matches,
        "seal_intact": seal_intact,
    }
    EXHIBIT_MACHINE.apply(session, exhibit, "reject", actor=actor, reason=reason, data=checks)
    _store_check(exhibit, actor, checks, None)
    exhibit.rejection_reason = reason.strip()
    return exhibit


def reconsider_exhibit(
    session: Session, *, actor: User, exhibit_id: uuid.UUID, reason: str
) -> Exhibit:
    exhibit = get_exhibit(session, actor, exhibit_id)
    _open_subcase(session, actor, exhibit.subcase_id)
    EXHIBIT_MACHINE.apply(session, exhibit, "reconsider", actor=actor, reason=reason)
    _store_check(
        exhibit,
        None,
        {"description_matches": None, "marking_matches": None, "seal_intact": None},
        None,
    )
    exhibit.rejection_reason = None
    return exhibit


def _store_check(
    exhibit: Exhibit, actor: User | None, checks: Mapping[str, bool | None], notes: str | None
) -> None:
    exhibit.description_matches = checks["description_matches"]
    exhibit.marking_matches = checks["marking_matches"]
    exhibit.seal_intact = checks["seal_intact"]
    exhibit.check_notes = notes.strip() if notes else None
    exhibit.checked_by = actor.id if actor else None


def list_exhibits(session: Session, subcase_id: uuid.UUID) -> list[Exhibit]:
    return list(
        session.execute(
            select(Exhibit).where(Exhibit.subcase_id == subcase_id).order_by(Exhibit.created_at)
        ).scalars()
    )


# --- Assignments (kept separate from physical custody, WF-03.03) -----------


def _replace_assignment(
    session: Session,
    *,
    actor: User,
    entity_type: str,
    entity_id: uuid.UUID,
    assignee: User,
    reason: str | None,
) -> AccessGrant:
    current = (
        session.execute(
            select(AccessGrant).where(
                AccessGrant.entity_type == entity_type,
                AccessGrant.entity_id == str(entity_id),
                AccessGrant.kind == GrantKind.ASSIGNMENT,
                AccessGrant.revoked_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    if any(g.user_id == assignee.id for g in current):
        raise DomainError(f"{assignee.display_name} is already assigned")
    for grant in current:
        if not reason:
            raise DomainError("Give a reason for reassigning this work")
        access.revoke(session, actor_id=actor.id, grant_id=grant.id, reason=reason)
    return access.grant(
        session,
        actor_id=actor.id,
        user_id=assignee.id,
        entity_type=entity_type,
        entity_id=entity_id,
        kind=GrantKind.ASSIGNMENT,
    )


def _colleague(
    session: Session, actor: User, user_id: uuid.UUID, role: Role, lab: uuid.UUID
) -> User:
    user = session.get(User, user_id)
    if user is None or not user.is_active or lab not in user.laboratory_ids:
        raise NotFound("Staff member not found in this laboratory")
    if role not in user.roles:
        raise DomainError(f"{user.display_name} is not a {role.value.replace('_', ' ')}")
    return user


def assign_case_scientist(
    session: Session,
    *,
    actor: User,
    subcase_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str | None = None,
) -> AccessGrant:
    """WF-03.01."""
    policy.require_roles(actor, policy.ASSIGNER_ROLES, "assign Case Scientists")
    subcase = _open_subcase(session, actor, subcase_id)
    scientist = _colleague(session, actor, user_id, Role.CASE_SCIENTIST, subcase.laboratory_id)
    return _replace_assignment(
        session,
        actor=actor,
        entity_type=policy.SUBCASE,
        entity_id=subcase.id,
        assignee=scientist,
        reason=reason,
    )


def assign_examination(
    session: Session,
    *,
    actor: User,
    exhibit_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> AccessGrant:
    """Assign an exhibit examination to a Screening Lab Officer, or claim it
    yourself by leaving user_id empty (WF-03.02)."""
    exhibit = get_exhibit(session, actor, exhibit_id)
    subcase = _open_subcase(session, actor, exhibit.subcase_id)
    if exhibit.state != ExhibitState.RECEIVED:
        raise InvalidTransition("Only received exhibits can be assigned for examination")
    if user_id is None or user_id == actor.id:
        if Role.SCREENING_LAB_OFFICER not in actor.roles:
            raise PermissionDenied("Only a Screening Lab Officer can claim an examination")
        officer = actor
    else:
        if not (
            Role.CASE_SCIENTIST in actor.roles
            and policy.is_assigned(session, actor, policy.SUBCASE, subcase.id)
        ) and not actor.has_role(Role.REVIEWER):
            raise PermissionDenied("Only the subcase's Case Scientist can assign examinations")
        officer = _colleague(
            session, actor, user_id, Role.SCREENING_LAB_OFFICER, subcase.laboratory_id
        )
    return _replace_assignment(
        session,
        actor=actor,
        entity_type=policy.EXHIBIT_EXAMINATION,
        entity_id=exhibit.id,
        assignee=officer,
        reason=reason,
    )


# --- Queues ----------------------------------------------------------------


def my_subcases(session: Session, user: User) -> list[Subcase]:
    ids = access.granted_entity_ids(session, user.id, policy.SUBCASE, kinds=(GrantKind.ASSIGNMENT,))
    if not ids:
        return []
    return list(
        session.execute(
            select(Subcase)
            .where(Subcase.id.in_([uuid.UUID(i) for i in ids]), Subcase.state == SubcaseState.OPEN)
            .order_by(Subcase.created_at)
        ).scalars()
    )


def my_examinations(session: Session, user: User) -> list[Exhibit]:
    ids = access.granted_entity_ids(
        session, user.id, policy.EXHIBIT_EXAMINATION, kinds=(GrantKind.ASSIGNMENT,)
    )
    if not ids:
        return []
    return list(
        session.execute(
            select(Exhibit)
            .where(Exhibit.id.in_([uuid.UUID(i) for i in ids]))
            .order_by(Exhibit.created_at)
        ).scalars()
    )


def search_cases(
    session: Session, user: User, text: str | None = None, limit: int = 50
) -> list[Case]:
    if not user.roles & policy.CASEWORK_ROLES or not user.laboratory_ids:
        return []
    query = (
        select(Case)
        .where(Case.laboratory_id.in_(user.laboratory_ids))
        .order_by(Case.created_at.desc())
        .limit(limit)
    )
    if text:
        like = f"%{text.strip()}%"
        query = query.where(Case.case_number.ilike(like) | Case.client_reference.ilike(like))
    return list(session.execute(query).scalars())

"""Chain of custody (WF-02.11, WF-03.04 to WF-03.10).

Custody is a history of movements per item. The current holder is never
stored separately; it is the latest effective movement, where an authorised
correction stands in for the entry it corrects while the original is kept.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import audit, sod
from app.core.errors import DomainError, InvalidTransition, NotFound, PermissionDenied
from app.modules.cases import policy
from app.modules.cases.models import Subcase
from app.modules.custody.models import (
    CorrectionState,
    CustodyCorrection,
    CustodyMovement,
    Handover,
    HandoverItem,
    HandoverItemState,
    MovementKind,
)
from app.modules.identity.models import User
from app.modules.items.models import Item
from app.modules.reference.models import Location


@dataclass(frozen=True)
class CustodyEntry:
    """One line of an item's custody history as it currently stands."""

    movement: CustodyMovement  # the effective record (a correction if one applies)
    original: CustodyMovement  # the movement as first recorded
    corrections: list[CustodyMovement]  # every authorised correction, oldest first

    @property
    def corrected(self) -> bool:
        return bool(self.corrections)


# --- Reading custody -------------------------------------------------------


def history(session: Session, item_id: uuid.UUID) -> list[CustodyEntry]:
    rows = list(
        session.execute(
            select(CustodyMovement)
            .where(CustodyMovement.item_id == item_id)
            .order_by(CustodyMovement.recorded_at, CustodyMovement.id)
        ).scalars()
    )
    corrections: dict[uuid.UUID, list[CustodyMovement]] = {}
    for row in rows:
        if row.corrects_movement_id:
            corrections.setdefault(row.corrects_movement_id, []).append(row)
    entries = [
        CustodyEntry(
            movement=(corrections.get(row.id) or [row])[-1],
            original=row,
            corrections=corrections.get(row.id, []),
        )
        for row in rows
        if row.corrects_movement_id is None
    ]
    entries.sort(key=lambda e: (e.movement.moved_at, e.original.recorded_at))
    return entries


def current(session: Session, item_id: uuid.UUID) -> CustodyMovement | None:
    entries = history(session, item_id)
    return entries[-1].movement if entries else None


def _lock_items(session: Session, item_ids: list[uuid.UUID]) -> None:
    """Serialise concurrent custody changes on the same items."""
    for item_id in sorted(item_ids):
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"custody:{item_id}"}
        )


def resolve_items(
    session: Session, actor: User, barcodes: list[str], verified_barcodes: list[str]
) -> list[Item]:
    """Look up the selected items and require every one to have been checked
    (scanned or confirmed) before the movement is completed (WF-03.07)."""
    selected = list(dict.fromkeys(b.strip() for b in barcodes if b.strip()))
    if not selected:
        raise DomainError("Select at least one item")
    verified = {b.strip() for b in verified_barcodes if b.strip()}
    missing = [b for b in selected if b not in verified]
    unexpected = sorted(verified - set(selected))
    if missing or unexpected:
        parts = []
        if missing:
            parts.append(f"not checked: {', '.join(missing)}")
        if unexpected:
            parts.append(f"checked but not selected: {', '.join(unexpected)}")
        raise DomainError("Item check does not match the selection (" + "; ".join(parts) + ")")

    items = {
        i.barcode: i
        for i in session.execute(select(Item).where(Item.barcode.in_(selected))).scalars()
    }
    if unknown := [b for b in selected if b not in items]:
        raise NotFound(f"Unknown barcodes: {', '.join(unknown)}")
    for item in items.values():
        _require_item_visible(session, actor, item)
    return [items[b] for b in selected]


def _require_item_visible(session: Session, actor: User, item: Item) -> Subcase:
    subcase = session.get(Subcase, item.subcase_id)
    assert subcase is not None
    policy.require_lab(actor, subcase.laboratory_id)
    return subcase


def _location(session: Session, location_id: uuid.UUID, laboratory_id: uuid.UUID) -> Location:
    location = session.get(Location, location_id)
    if location is None or location.laboratory_id != laboratory_id:
        raise NotFound("Location not found")
    if not location.active:
        raise DomainError(f"Location {location.code} is not in use")
    return location


def _pending_handover(session: Session, item_id: uuid.UUID) -> HandoverItem | None:
    return session.execute(
        select(HandoverItem).where(
            HandoverItem.item_id == item_id, HandoverItem.state == HandoverItemState.PENDING
        )
    ).scalar_one_or_none()


def _now(session: Session) -> datetime:
    value: datetime = session.execute(text("SELECT clock_timestamp()")).scalar_one()
    return value


def _record(
    session: Session,
    *,
    actor: User,
    item: Item,
    kind: MovementKind,
    previous: CustodyMovement | None,
    to_person_id: uuid.UUID | None,
    to_location_id: uuid.UUID | None,
    group_id: uuid.UUID,
    moved_at: datetime,
    note: str | None = None,
    corrects: CustodyMovement | None = None,
    reason: str | None = None,
) -> CustodyMovement:
    if to_person_id is None and to_location_id is None:
        raise DomainError("A movement needs a destination person, location, or both")
    if corrects is not None:
        from_person, from_location = corrects.from_person_id, corrects.from_location_id
    else:
        from_person = previous.to_person_id if previous else None
        from_location = previous.to_location_id if previous else None
    movement = CustodyMovement(
        item_id=item.id,
        kind=kind,
        from_person_id=from_person,
        from_location_id=from_location,
        to_person_id=to_person_id,
        to_location_id=to_location_id,
        moved_at=moved_at,
        recorded_by=actor.id,
        group_id=group_id,
        corrects_movement_id=corrects.id if corrects else None,
        note=note,
    )
    session.add(movement)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action=f"custody.{kind.value}",
        entity_type="item",
        entity_id=item.id,
        reason=reason,
        before={
            "person_id": from_person,
            "location_id": from_location,
        },
        after={
            "barcode": item.barcode,
            "movement_id": movement.id,
            "person_id": to_person_id,
            "location_id": to_location_id,
            "moved_at": moved_at,
            "group_id": group_id,
            "corrects_movement_id": corrects.id if corrects else None,
        },
    )
    return movement


# --- Receipt ---------------------------------------------------------------


def record_receipt(session: Session, *, actor: User, items: list[Item]) -> list[CustodyMovement]:
    """First custody entry: the receiving staff member holds the exhibits."""
    _lock_items(session, [i.id for i in items])
    group, now = uuid.uuid4(), _now(session)
    movements = []
    for item in items:
        if current(session, item.id) is not None:
            raise InvalidTransition(f"{item.barcode} already has a custody record")
        movements.append(
            _record(
                session,
                actor=actor,
                item=item,
                kind=MovementKind.RECEIPT,
                previous=None,
                to_person_id=actor.id,
                to_location_id=None,
                group_id=group,
                moved_at=now,
                note="Received from submitter",
            )
        )
    return movements


# --- Moving items ----------------------------------------------------------


def move(
    session: Session,
    *,
    actor: User,
    barcodes: list[str],
    verified_barcodes: list[str],
    to_location_id: uuid.UUID | None,
    keep_with_me: bool,
    note: str | None = None,
) -> list[CustodyMovement]:
    """Retrieve, store or batch-move items to one common destination
    (WF-03.04 to WF-03.07). Giving items to another person is a handover."""
    policy.require_roles(actor, policy.CUSTODY_ROLES, "move items")
    if to_location_id is None and not keep_with_me:
        raise DomainError("Choose a destination location, or take the items yourself")
    items = resolve_items(session, actor, barcodes, verified_barcodes)
    _lock_items(session, [i.id for i in items])
    labs = {_require_item_visible(session, actor, i).laboratory_id for i in items}
    if len(labs) != 1:
        raise DomainError("Items from different laboratories cannot be moved together")
    location = _location(session, to_location_id, labs.pop()) if to_location_id else None

    previous_by_item = {}
    for item in items:
        previous = current(session, item.id)
        if previous is None:
            raise InvalidTransition(f"{item.barcode} has not been received yet")
        if previous.to_person_id not in (None, actor.id):
            holder = session.get(User, previous.to_person_id)
            raise PermissionDenied(
                f"{item.barcode} is held by {holder.display_name if holder else 'someone else'}; "
                "they must hand it over"
            )
        if _pending_handover(session, item.id):
            raise InvalidTransition(f"{item.barcode} is waiting in a handover; withdraw it first")
        previous_by_item[item.id] = previous

    group, now = uuid.uuid4(), _now(session)
    return [
        _record(
            session,
            actor=actor,
            item=item,
            kind=MovementKind.MOVE,
            previous=previous_by_item[item.id],
            to_person_id=actor.id if keep_with_me else None,
            to_location_id=location.id if location else None,
            group_id=group,
            moved_at=now,
            note=note,
        )
        for item in items
    ]


# --- Handover --------------------------------------------------------------


def create_handover(
    session: Session,
    *,
    actor: User,
    barcodes: list[str],
    verified_barcodes: list[str],
    to_person_id: uuid.UUID,
    note: str | None = None,
) -> Handover:
    policy.require_roles(actor, policy.CUSTODY_ROLES, "hand over items")
    items = resolve_items(session, actor, barcodes, verified_barcodes)
    _lock_items(session, [i.id for i in items])
    receiver = session.get(User, to_person_id)
    lab_ids = {_require_item_visible(session, actor, i).laboratory_id for i in items}
    if (
        receiver is None
        or not receiver.is_active
        or not receiver.roles & policy.CUSTODY_ROLES
        or not lab_ids <= receiver.laboratory_ids
    ):
        raise NotFound("Receiving staff member not found in this laboratory")
    if receiver.id == actor.id:
        raise DomainError("You cannot hand items over to yourself")
    for item in items:
        holder = current(session, item.id)
        if holder is None or holder.to_person_id != actor.id:
            raise PermissionDenied(f"You do not hold {item.barcode}")
        if _pending_handover(session, item.id):
            raise InvalidTransition(f"{item.barcode} is already waiting in a handover")

    handover = Handover(from_person_id=actor.id, to_person_id=receiver.id, note=note)
    session.add(handover)
    session.flush()
    for item in items:
        session.add(HandoverItem(handover_id=handover.id, item_id=item.id))
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="handover.offered",
        entity_type="handover",
        entity_id=handover.id,
        after={"to_person_id": receiver.id, "items": [i.barcode for i in items], "note": note},
    )
    return handover


def _handover_items(
    session: Session, handover: Handover, item_ids: list[uuid.UUID]
) -> list[HandoverItem]:
    rows = {
        r.item_id: r
        for r in session.execute(
            select(HandoverItem).where(
                HandoverItem.handover_id == handover.id,
                HandoverItem.state == HandoverItemState.PENDING,
            )
        ).scalars()
    }
    if not item_ids or any(i not in rows for i in item_ids):
        raise DomainError("Select items that are still waiting in this handover")
    return [rows[i] for i in item_ids]


def accept_handover(
    session: Session,
    *,
    actor: User,
    handover_id: uuid.UUID,
    barcodes: list[str],
    verified_barcodes: list[str],
    to_location_id: uuid.UUID | None = None,
) -> list[CustodyMovement]:
    """The designated receiver signs in and accepts selected items (WF-03.08)."""
    handover = session.get(Handover, handover_id)
    if handover is None:
        raise NotFound("Handover not found")
    sod.require_designated_person(sod.HANDOVER_RECEIVER_ACCEPTS, actor, handover.to_person_id)
    items = resolve_items(session, actor, barcodes, verified_barcodes)
    _lock_items(session, [i.id for i in items])
    rows = _handover_items(session, handover, [i.id for i in items])
    lab = _require_item_visible(session, actor, items[0]).laboratory_id
    location = _location(session, to_location_id, lab) if to_location_id else None

    group, now = uuid.uuid4(), _now(session)
    movements = []
    for item, row in zip(items, rows, strict=True):
        previous = current(session, item.id)
        if previous is None or previous.to_person_id != handover.from_person_id:
            raise InvalidTransition(f"{item.barcode} is no longer held by the sender")
        movement = _record(
            session,
            actor=actor,
            item=item,
            kind=MovementKind.HANDOVER,
            previous=previous,
            to_person_id=actor.id,
            to_location_id=location.id if location else None,
            group_id=group,
            moved_at=now,
            note=handover.note,
        )
        row.state = HandoverItemState.ACCEPTED
        row.movement_id = movement.id
        movements.append(movement)
    return movements


def withdraw_handover(
    session: Session, *, actor: User, handover_id: uuid.UUID, item_ids: list[uuid.UUID], reason: str
) -> None:
    handover = session.get(Handover, handover_id)
    if handover is None or handover.from_person_id != actor.id:
        raise NotFound("Handover not found")
    rows = _handover_items(session, handover, item_ids)
    for row in rows:
        row.state = HandoverItemState.WITHDRAWN
    audit.record(
        session,
        actor_id=actor.id,
        action="handover.withdrawn",
        entity_type="handover",
        entity_id=handover.id,
        reason=reason,
        after={"item_ids": item_ids},
    )


def pending_handovers_for(session: Session, user: User) -> list[tuple[Handover, list[Item]]]:
    rows = session.execute(
        select(Handover, Item)
        .join(HandoverItem, HandoverItem.handover_id == Handover.id)
        .join(Item, Item.id == HandoverItem.item_id)
        .where(Handover.to_person_id == user.id, HandoverItem.state == HandoverItemState.PENDING)
        .order_by(Handover.created_at, Item.barcode)
    ).all()
    grouped: dict[uuid.UUID, tuple[Handover, list[Item]]] = {}
    for handover, item in rows:
        grouped.setdefault(handover.id, (handover, []))[1].append(item)
    return list(grouped.values())


# --- Corrections -----------------------------------------------------------


def request_correction(
    session: Session,
    *,
    actor: User,
    movement_id: uuid.UUID,
    reason: str,
    to_person_id: uuid.UUID | None,
    to_location_id: uuid.UUID | None,
    moved_at: datetime | None = None,
    authorize_now: bool = False,
) -> CustodyCorrection:
    """Request (or, for an authoriser, request and authorise) the correction of
    an earlier custody entry (WF-03.10)."""
    policy.require_roles(actor, policy.CUSTODY_ROLES, "request custody corrections")
    if not reason or not reason.strip():
        raise DomainError("A custody correction needs a reason")
    movement = session.get(CustodyMovement, movement_id)
    if movement is None:
        raise NotFound("Custody entry not found")
    if movement.corrects_movement_id is not None:
        raise DomainError("Correct the original entry, not an earlier correction")
    item = session.get(Item, movement.item_id)
    assert item is not None
    lab = _require_item_visible(session, actor, item).laboratory_id
    if to_location_id:
        _location(session, to_location_id, lab)
    if to_person_id:
        person = session.get(User, to_person_id)
        if person is None or lab not in person.laboratory_ids:
            raise NotFound("Staff member not found in this laboratory")
    if to_person_id is None and to_location_id is None:
        raise DomainError("A corrected entry needs a person, a location, or both")
    if moved_at is not None and moved_at > datetime.now(UTC):
        raise DomainError("The corrected time cannot be in the future")

    correction = CustodyCorrection(
        movement_id=movement.id,
        reason=reason.strip(),
        to_person_id=to_person_id,
        to_location_id=to_location_id,
        moved_at=moved_at or movement.moved_at,
        requested_by=actor.id,
    )
    session.add(correction)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="custody.correction_requested",
        entity_type="item",
        entity_id=item.id,
        reason=correction.reason,
        before={
            "movement_id": movement.id,
            "person_id": movement.to_person_id,
            "location_id": movement.to_location_id,
            "moved_at": movement.moved_at,
        },
        after={
            "correction_id": correction.id,
            "person_id": to_person_id,
            "location_id": to_location_id,
            "moved_at": correction.moved_at,
        },
    )
    if authorize_now:
        decide_correction(
            session, actor=actor, correction_id=correction.id, authorize=True, note=reason
        )
    return correction


def decide_correction(
    session: Session, *, actor: User, correction_id: uuid.UUID, authorize: bool, note: str
) -> CustodyCorrection:
    policy.require_roles(actor, policy.CORRECTION_AUTHORIZER_ROLES, "authorise custody corrections")
    correction = session.get(CustodyCorrection, correction_id)
    if correction is None:
        raise NotFound("Correction not found")
    if correction.state != CorrectionState.REQUESTED:
        raise InvalidTransition("This correction has already been decided")
    if not note or not note.strip():
        raise DomainError("Record the reason for your decision")
    original = session.get(CustodyMovement, correction.movement_id)
    assert original is not None
    item = session.get(Item, original.item_id)
    assert item is not None
    _require_item_visible(session, actor, item)
    _lock_items(session, [item.id])

    correction.state = CorrectionState.AUTHORIZED if authorize else CorrectionState.DECLINED
    correction.decided_by = actor.id
    correction.decided_at = _now(session)
    correction.decision_note = note.strip()
    if authorize:
        movement = _record(
            session,
            actor=actor,
            item=item,
            kind=MovementKind.CORRECTION,
            previous=None,
            to_person_id=correction.to_person_id,
            to_location_id=correction.to_location_id,
            group_id=original.group_id,
            moved_at=correction.moved_at,
            note=correction.reason,
            corrects=original,
            reason=correction.reason,
        )
        correction.correction_movement_id = movement.id
    else:
        audit.record(
            session,
            actor_id=actor.id,
            action="custody.correction_declined",
            entity_type="item",
            entity_id=item.id,
            reason=note.strip(),
            after={"correction_id": correction.id},
        )
    return correction


def pending_corrections(session: Session, actor: User) -> list[CustodyCorrection]:
    rows = session.execute(
        select(CustodyCorrection, Item, Subcase)
        .join(CustodyMovement, CustodyMovement.id == CustodyCorrection.movement_id)
        .join(Item, Item.id == CustodyMovement.item_id)
        .join(Subcase, Subcase.id == Item.subcase_id)
        .where(
            CustodyCorrection.state == CorrectionState.REQUESTED,
            Subcase.laboratory_id.in_(actor.laboratory_ids),
        )
        .order_by(CustodyCorrection.created_at)
    ).all()
    return [c for c, _, _ in rows]

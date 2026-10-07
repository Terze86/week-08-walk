import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.errors import NotFound
from app.modules.cases.router import person
from app.modules.cases.schemas import Person
from app.modules.cases.service import get_subcase
from app.modules.custody import service
from app.modules.custody.models import (
    CorrectionState,
    CustodyCorrection,
    CustodyMovement,
    MovementKind,
)
from app.modules.items.models import Item, ItemKind
from app.modules.reference.models import Location

router = APIRouter(prefix="/custody", tags=["custody"])
Db = Annotated[Session, Depends(get_db)]


class Selection(BaseModel):
    barcodes: list[str] = Field(min_length=1)
    verified_barcodes: list[str]


class MoveIn(Selection):
    to_location_id: uuid.UUID | None = None
    keep_with_me: bool = False
    note: str | None = Field(default=None, max_length=500)


class HandoverIn(Selection):
    to_person_id: uuid.UUID
    note: str | None = Field(default=None, max_length=500)


class AcceptHandoverIn(Selection):
    to_location_id: uuid.UUID | None = None


class WithdrawIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=1)
    reason: str = Field(min_length=3)


class CorrectionIn(BaseModel):
    reason: str = Field(min_length=3)
    to_person_id: uuid.UUID | None = None
    to_location_id: uuid.UUID | None = None
    moved_at: datetime | None = None
    authorize_now: bool = False


class DecisionIn(BaseModel):
    authorize: bool
    note: str = Field(min_length=3)


class Place(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class MovementOut(BaseModel):
    id: uuid.UUID
    kind: MovementKind
    from_person: Person | None
    from_location: Place | None
    to_person: Person | None
    to_location: Place | None
    moved_at: datetime
    recorded_at: datetime
    recorded_by: Person | None
    note: str | None


class EntryOut(BaseModel):
    movement: MovementOut
    original: MovementOut | None  # present only when the entry was corrected
    corrections: list[MovementOut]


class ItemOut(BaseModel):
    id: uuid.UUID
    barcode: str
    kind: ItemKind
    label: str
    subcase_id: uuid.UUID
    current: MovementOut | None
    history: list[EntryOut]


class CorrectionOut(BaseModel):
    id: uuid.UUID
    state: CorrectionState
    barcode: str
    reason: str
    requested_by: Person | None
    original: MovementOut
    to_person: Person | None
    to_location: Place | None
    moved_at: datetime


class HandoverOut(BaseModel):
    id: uuid.UUID
    from_person: Person | None
    note: str | None
    created_at: datetime
    items: list[dict[str, str]]


def place(db: Session, location_id: uuid.UUID | None) -> Place | None:
    loc = db.get(Location, location_id) if location_id else None
    return Place(id=loc.id, code=loc.code, name=loc.name) if loc else None


def movement_out(db: Session, m: CustodyMovement) -> MovementOut:
    return MovementOut(
        id=m.id,
        kind=m.kind,
        from_person=person(db, m.from_person_id),
        from_location=place(db, m.from_location_id),
        to_person=person(db, m.to_person_id),
        to_location=place(db, m.to_location_id),
        moved_at=m.moved_at,
        recorded_at=m.recorded_at,
        recorded_by=person(db, m.recorded_by),
        note=m.note,
    )


def item_out(db: Session, item: Item) -> ItemOut:
    entries = service.history(db, item.id)
    return ItemOut(
        id=item.id,
        barcode=item.barcode,
        kind=item.kind,
        label=item.label,
        subcase_id=item.subcase_id,
        current=movement_out(db, entries[-1].movement) if entries else None,
        history=[
            EntryOut(
                movement=movement_out(db, e.movement),
                original=movement_out(db, e.original) if e.corrected else None,
                corrections=[movement_out(db, c) for c in e.corrections],
            )
            for e in entries
        ],
    )


def _items(db: Session, movements: list[CustodyMovement]) -> list[ItemOut]:
    return [item_out(db, db.get(Item, m.item_id)) for m in movements]  # type: ignore[arg-type]


@router.get("/items/{barcode}", response_model=ItemOut)
def item(barcode: str, db: Db, user: CurrentUser) -> ItemOut:
    found = db.execute(select(Item).where(Item.barcode == barcode.strip())).scalar_one_or_none()
    if found is None:
        raise NotFound("Unknown barcode")
    get_subcase(db, user, found.subcase_id)
    return item_out(db, found)


@router.post("/move", response_model=list[ItemOut])
def move(body: MoveIn, db: Db, user: CurrentUser) -> list[ItemOut]:
    return _items(db, service.move(db, actor=user, **body.model_dump()))


@router.post("/handovers", status_code=201)
def offer(body: HandoverIn, db: Db, user: CurrentUser) -> dict[str, uuid.UUID]:
    handover = service.create_handover(db, actor=user, **body.model_dump())
    return {"id": handover.id}


@router.get("/handovers/incoming", response_model=list[HandoverOut])
def incoming(db: Db, user: CurrentUser) -> list[HandoverOut]:
    return [
        HandoverOut(
            id=h.id,
            from_person=person(db, h.from_person_id),
            note=h.note,
            created_at=h.created_at,
            items=[{"id": str(i.id), "barcode": i.barcode, "label": i.label} for i in items],
        )
        for h, items in service.pending_handovers_for(db, user)
    ]


@router.post("/handovers/{handover_id}/accept", response_model=list[ItemOut])
def accept(
    handover_id: uuid.UUID, body: AcceptHandoverIn, db: Db, user: CurrentUser
) -> list[ItemOut]:
    return _items(
        db, service.accept_handover(db, actor=user, handover_id=handover_id, **body.model_dump())
    )


@router.post("/handovers/{handover_id}/withdraw", status_code=204)
def withdraw(handover_id: uuid.UUID, body: WithdrawIn, db: Db, user: CurrentUser) -> None:
    service.withdraw_handover(db, actor=user, handover_id=handover_id, **body.model_dump())


def correction_out(db: Session, c: CustodyCorrection) -> CorrectionOut:
    original = db.get(CustodyMovement, c.movement_id)
    assert original is not None
    found = db.get(Item, original.item_id)
    assert found is not None
    return CorrectionOut(
        id=c.id,
        state=c.state,
        barcode=found.barcode,
        reason=c.reason,
        requested_by=person(db, c.requested_by),
        original=movement_out(db, original),
        to_person=person(db, c.to_person_id),
        to_location=place(db, c.to_location_id),
        moved_at=c.moved_at,
    )


@router.post("/movements/{movement_id}/corrections", response_model=CorrectionOut, status_code=201)
def request_correction(
    movement_id: uuid.UUID, body: CorrectionIn, db: Db, user: CurrentUser
) -> CorrectionOut:
    correction = service.request_correction(
        db, actor=user, movement_id=movement_id, **body.model_dump()
    )
    return correction_out(db, correction)


@router.get("/corrections/pending", response_model=list[CorrectionOut])
def pending_corrections(db: Db, user: CurrentUser) -> list[CorrectionOut]:
    return [correction_out(db, c) for c in service.pending_corrections(db, user)]


@router.post("/corrections/{correction_id}/decision", response_model=CorrectionOut)
def decide(correction_id: uuid.UUID, body: DecisionIn, db: Db, user: CurrentUser) -> CorrectionOut:
    correction = service.decide_correction(
        db, actor=user, correction_id=correction_id, authorize=body.authorize, note=body.note
    )
    return correction_out(db, correction)

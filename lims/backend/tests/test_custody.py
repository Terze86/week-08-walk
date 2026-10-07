from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import (
    DomainError,
    InvalidTransition,
    NotFound,
    PermissionDenied,
    SeparationOfDutiesViolation,
)
from app.modules.custody import service as custody
from app.modules.custody.models import CorrectionState, MovementKind
from app.modules.items.models import Item
from app.modules.reference import service as reference


def codes(db: Session, exhibits) -> list[str]:
    return [db.get(Item, e.id).barcode for e in exhibits]


@pytest.mark.urs("WF-02.11", "WF-03.04", "WF-03.05")
def test_store_and_retrieve_records_source_destination_and_time(
    db: Session, staff, setting, received
) -> None:
    _, (shirt, knife) = received
    cs, slo = staff["cs1"], staff["slo1"]
    [code] = codes(db, [shirt])
    custody.move(
        db,
        actor=cs,
        barcodes=[code],
        verified_barcodes=[code],
        to_location_id=setting.store_a.id,
        keep_with_me=False,
    )
    stored = custody.current(db, shirt.id)
    assert stored.from_person_id == cs.id and stored.to_location_id == setting.store_a.id
    assert stored.to_person_id is None and stored.moved_at is not None

    # Another officer retrieves it from storage to the bench, keeping it with them.
    custody.move(
        db,
        actor=slo,
        barcodes=[code],
        verified_barcodes=[code],
        to_location_id=setting.bench.id,
        keep_with_me=True,
    )
    now = custody.current(db, shirt.id)
    assert (now.from_location_id, now.to_person_id, now.to_location_id) == (
        setting.store_a.id,
        slo.id,
        setting.bench.id,
    )
    assert [e.movement.kind for e in custody.history(db, shirt.id)] == [
        MovementKind.RECEIPT,
        MovementKind.MOVE,
        MovementKind.MOVE,
    ]
    assert [e.action for e in audit.history(db, "item", shirt.id)] == [
        "custody.receipt",
        "custody.move",
        "custody.move",
    ]


@pytest.mark.urs("WF-03.06", "WF-03.07")
def test_batch_move_requires_every_selected_item_checked(
    db: Session, staff, setting, received
) -> None:
    _, exhibits = received
    cs = staff["cs1"]
    selected = codes(db, exhibits)
    with pytest.raises(DomainError, match="not checked"):
        custody.move(
            db,
            actor=cs,
            barcodes=selected,
            verified_barcodes=selected[:1],
            to_location_id=setting.store_a.id,
            keep_with_me=False,
        )
    with pytest.raises(DomainError, match="checked but not selected"):
        custody.move(
            db,
            actor=cs,
            barcodes=selected[:1],
            verified_barcodes=selected,
            to_location_id=setting.store_a.id,
            keep_with_me=False,
        )
    moves = custody.move(
        db,
        actor=cs,
        barcodes=selected,
        verified_barcodes=list(reversed(selected)),
        to_location_id=setting.store_b.id,
        keep_with_me=False,
    )
    assert {m.to_location_id for m in moves} == {setting.store_b.id}
    assert len({m.group_id for m in moves}) == 1


def test_cannot_take_an_item_someone_else_holds(db: Session, staff, setting, received) -> None:
    _, (shirt, _) = received
    [code] = codes(db, [shirt])
    with pytest.raises(PermissionDenied, match="hand it over"):
        custody.move(
            db,
            actor=staff["slo1"],
            barcodes=[code],
            verified_barcodes=[code],
            to_location_id=setting.bench.id,
            keep_with_me=True,
        )


def test_inactive_or_unknown_destinations_are_refused(
    db: Session, staff, setting, received
) -> None:
    _, (shirt, _) = received
    [code] = codes(db, [shirt])
    reference.set_location_active(
        db, actor=staff["admin1"], location_id=setting.store_b.id, active=False, reason="Full"
    )
    with pytest.raises(DomainError, match="not in use"):
        custody.move(
            db,
            actor=staff["cs1"],
            barcodes=[code],
            verified_barcodes=[code],
            to_location_id=setting.store_b.id,
            keep_with_me=False,
        )
    with pytest.raises(NotFound):
        custody.move(
            db,
            actor=staff["cs1"],
            barcodes=["EX-NOPE"],
            verified_barcodes=["EX-NOPE"],
            to_location_id=setting.store_a.id,
            keep_with_me=False,
        )


@pytest.mark.urs("WF-03.08")
def test_handover_is_completed_only_by_the_designated_receiver(
    db: Session, staff, setting, received
) -> None:
    _, exhibits = received
    cs, slo, dlo = staff["cs1"], staff["slo1"], staff["dlo1"]
    shirt_code, knife_code = codes(db, exhibits)
    handover = custody.create_handover(
        db,
        actor=cs,
        barcodes=[shirt_code, knife_code],
        verified_barcodes=[shirt_code, knife_code],
        to_person_id=slo.id,
        note="For screening",
    )
    # Items waiting in a handover cannot be moved meanwhile.
    with pytest.raises(InvalidTransition, match="handover"):
        custody.move(
            db,
            actor=cs,
            barcodes=[shirt_code],
            verified_barcodes=[shirt_code],
            to_location_id=setting.store_a.id,
            keep_with_me=False,
        )
    with pytest.raises(SeparationOfDutiesViolation):
        custody.accept_handover(
            db,
            actor=dlo,
            handover_id=handover.id,
            barcodes=[shirt_code],
            verified_barcodes=[shirt_code],
        )
    assert [h.id for h, _ in custody.pending_handovers_for(db, slo)] == [handover.id]

    # The receiver accepts only the shirt; the sender withdraws the knife.
    custody.accept_handover(
        db,
        actor=slo,
        handover_id=handover.id,
        barcodes=[shirt_code],
        verified_barcodes=[shirt_code],
        to_location_id=setting.bench.id,
    )
    custody.withdraw_handover(
        db,
        actor=cs,
        handover_id=handover.id,
        item_ids=[exhibits[1].id],
        reason="Knife not needed yet",
    )
    shirt_now = custody.current(db, exhibits[0].id)
    assert shirt_now.kind == MovementKind.HANDOVER
    assert (shirt_now.from_person_id, shirt_now.to_person_id) == (cs.id, slo.id)
    assert custody.current(db, exhibits[1].id).to_person_id == cs.id
    assert custody.pending_handovers_for(db, slo) == []


def test_handover_requires_holding_the_items(db: Session, staff, received) -> None:
    _, (shirt, _) = received
    [code] = codes(db, [shirt])
    with pytest.raises(PermissionDenied):
        custody.create_handover(
            db,
            actor=staff["slo1"],
            barcodes=[code],
            verified_barcodes=[code],
            to_person_id=staff["dlo1"].id,
        )
    with pytest.raises(NotFound):
        custody.create_handover(
            db,
            actor=staff["cs1"],
            barcodes=[code],
            verified_barcodes=[code],
            to_person_id=staff["codis1"].id,
        )


@pytest.mark.urs("WF-03.10")
def test_correction_is_authorised_and_keeps_the_original(
    db: Session, staff, setting, received
) -> None:
    _, (shirt, _) = received
    cs, dlo, rev = staff["cs1"], staff["dlo1"], staff["rev1"]
    [code] = codes(db, [shirt])
    [wrong] = custody.move(
        db,
        actor=cs,
        barcodes=[code],
        verified_barcodes=[code],
        to_location_id=setting.store_a.id,
        keep_with_me=False,
    )
    # A DNA Lab Officer may request but not authorise.
    correction = custody.request_correction(
        db,
        actor=dlo,
        movement_id=wrong.id,
        reason="Actually placed in store B",
        to_person_id=None,
        to_location_id=setting.store_b.id,
    )
    with pytest.raises(PermissionDenied):
        custody.decide_correction(
            db, actor=dlo, correction_id=correction.id, authorize=True, note="ok"
        )
    assert custody.current(db, shirt.id).to_location_id == setting.store_a.id  # not yet

    custody.decide_correction(
        db, actor=rev, correction_id=correction.id, authorize=True, note="Confirmed with cs1"
    )
    assert correction.state == CorrectionState.AUTHORIZED
    entry = custody.history(db, shirt.id)[-1]
    assert entry.corrected and entry.original.id == wrong.id
    assert entry.original.to_location_id == setting.store_a.id  # original retained
    assert entry.movement.to_location_id == setting.store_b.id
    assert custody.current(db, shirt.id).to_location_id == setting.store_b.id
    with pytest.raises(InvalidTransition):
        custody.decide_correction(
            db, actor=rev, correction_id=correction.id, authorize=False, note="again"
        )
    with pytest.raises(DomainError, match="original entry"):
        custody.request_correction(
            db,
            actor=rev,
            movement_id=entry.movement.id,
            reason="r",
            to_person_id=None,
            to_location_id=setting.store_a.id,
        )


def test_authoriser_can_request_and_authorise_in_one_step_and_correct_time(
    db: Session, staff, setting, received
) -> None:
    _, (shirt, _) = received
    rev, cs = staff["rev1"], staff["cs1"]
    receipt_entry = custody.current(db, shirt.id)
    earlier = receipt_entry.moved_at - timedelta(minutes=20)
    custody.request_correction(
        db,
        actor=rev,
        movement_id=receipt_entry.id,
        reason="Receipt time entered late",
        to_person_id=cs.id,
        to_location_id=None,
        moved_at=earlier,
        authorize_now=True,
    )
    assert custody.current(db, shirt.id).moved_at == earlier


def test_declined_correction_changes_nothing(db: Session, staff, setting, received) -> None:
    _, (shirt, _) = received
    original = custody.current(db, shirt.id)
    correction = custody.request_correction(
        db,
        actor=staff["dlo1"],
        movement_id=original.id,
        reason="I think it went to the bench",
        to_person_id=None,
        to_location_id=setting.bench.id,
    )
    custody.decide_correction(
        db,
        actor=staff["cs1"],
        correction_id=correction.id,
        authorize=False,
        note="Receipt record is correct",
    )
    assert custody.current(db, shirt.id).id == original.id
    assert correction.state == CorrectionState.DECLINED

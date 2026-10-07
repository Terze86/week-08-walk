import pytest
from sqlalchemy.orm import Session

from app.core import documents
from app.core.errors import DomainError, InvalidTransition, PermissionDenied
from app.core.files import read_file
from app.modules.cases import service as cases
from app.modules.cases.models import ExhibitState
from app.modules.custody import service as custody
from app.modules.custody.models import MovementKind
from app.modules.receipt import service as receipts
from app.modules.receipt.models import ExceptionKind, ReceiptState
from tests.casework import SIGNATURE_PNG, accepted, register


@pytest.fixture
def subcase_with_exhibits(db: Session, staff, lab, setting):
    cs = staff["cs1"]
    _, subcase = register(db, cs, lab, setting)
    shirt = accepted(db, cs, subcase, "Blue shirt")
    knife = accepted(db, cs, subcase, "Knife")
    swab = cases.add_exhibit(db, actor=cs, subcase_id=subcase.id, description="Swab")
    cases.reject_exhibit(db, actor=cs, exhibit_id=swab.id, reason="Container leaking")
    return subcase, shirt, knife, swab


@pytest.mark.urs("WF-02.07", "WF-02.08", "WF-02.09")
def test_signed_receipt_is_retained_and_exhibits_received(
    db: Session, staff, subcase_with_exhibits, file_store
) -> None:
    subcase, shirt, knife, swab = subcase_with_exhibits
    cs = staff["cs1"]
    with pytest.raises(InvalidTransition):
        receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[swab.id])
    receipt = receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])
    assert receipt.actual_submitter_name == "SSgt Tan"  # defaulted from the case
    assert [e.id for e in receipts.rejected_exhibits(db, subcase.id)] == [swab.id]

    with pytest.raises(DomainError, match="PNG"):
        receipts.complete_receipt(
            db,
            actor=cs,
            store=file_store,
            receipt_id=receipt.id,
            signature_png=b"not an image",
            actual_submitter_name="Cpl Ong",
        )
    receipts.complete_receipt(
        db,
        actor=cs,
        store=file_store,
        receipt_id=receipt.id,
        signature_png=SIGNATURE_PNG,
        actual_submitter_name="Cpl Ong",
    )
    assert receipt.state == ReceiptState.COMPLETED
    assert receipt.receiving_staff_id == cs.id and receipt.actual_submitter_name == "Cpl Ong"
    assert shirt.state == ExhibitState.RECEIVED and knife.state == ExhibitState.ACCEPTED

    # The retained record: an immutable document version holding the receipt
    # content and the signature image.
    version = documents.latest_version(db, receipt.record_document_id)
    documents.verify_version(db, version)
    content = version.content
    assert content["actual_submitter"] == "Cpl Ong"
    assert content["receiving_staff"]["id"] == str(cs.id)
    assert [x["description"] for x in content["accepted_exhibits"]] == ["Blue shirt"]
    assert [x["rejection_reason"] for x in content["rejected_exhibits"]] == ["Container leaking"]
    _, image = read_file(db, file_store, version.file_id)
    assert image == SIGNATURE_PNG

    first = custody.current(db, shirt.id)
    assert first.kind == MovementKind.RECEIPT and first.to_person_id == cs.id


def test_exhibit_cannot_be_on_two_receipts(db: Session, staff, subcase_with_exhibits) -> None:
    subcase, shirt, _, _ = subcase_with_exhibits
    cs = staff["cs1"]
    receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])
    with pytest.raises(InvalidTransition, match="already on a receipt"):
        receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])


@pytest.mark.urs("WF-02.10")
def test_handover_exception_is_kept_for_follow_up(
    db: Session, staff, subcase_with_exhibits, file_store
) -> None:
    subcase, shirt, knife, _ = subcase_with_exhibits
    cs = staff["cs1"]
    receipt = receipts.prepare_receipt(
        db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id, knife.id]
    )
    with pytest.raises(DomainError):
        receipts.record_exception(
            db, actor=cs, receipt_id=receipt.id, kind=ExceptionKind.SUBMITTER_REFUSED, note=""
        )
    receipts.record_exception(
        db,
        actor=cs,
        receipt_id=receipt.id,
        kind=ExceptionKind.SUBMITTER_REFUSED,
        note="Submitter refused to sign without supervisor present",
    )
    assert [r.id for r in receipts.open_exceptions(db, cs)] == [receipt.id]
    with pytest.raises(InvalidTransition):
        receipts.complete_receipt(
            db,
            actor=cs,
            store=file_store,
            receipt_id=receipt.id,
            signature_png=SIGNATURE_PNG,
            actual_submitter_name="SSgt Tan",
        )
    receipts.retry_receipt(db, actor=cs, receipt_id=receipt.id, note="Supervisor now present")
    receipts.complete_receipt(
        db,
        actor=cs,
        store=file_store,
        receipt_id=receipt.id,
        signature_png=SIGNATURE_PNG,
        actual_submitter_name="SSgt Tan",
    )
    assert receipts.open_exceptions(db, cs) == []


def test_cancelled_receipt_frees_its_exhibits(db: Session, staff, subcase_with_exhibits) -> None:
    subcase, shirt, _, _ = subcase_with_exhibits
    cs = staff["cs1"]
    first = receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])
    receipts.cancel_receipt(db, actor=cs, receipt_id=first.id, reason="Wrong exhibits selected")
    second = receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])
    assert second.receipt_number != first.receipt_number


def test_only_reception_roles_complete_receipts(
    db: Session, staff, subcase_with_exhibits, file_store
) -> None:
    subcase, shirt, _, _ = subcase_with_exhibits
    receipt = receipts.prepare_receipt(
        db, actor=staff["cs1"], subcase_id=subcase.id, exhibit_ids=[shirt.id]
    )
    with pytest.raises(PermissionDenied):
        receipts.complete_receipt(
            db,
            actor=staff["dlo1"],
            store=file_store,
            receipt_id=receipt.id,
            signature_png=SIGNATURE_PNG,
            actual_submitter_name="X",
        )

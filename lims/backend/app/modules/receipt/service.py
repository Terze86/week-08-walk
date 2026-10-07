"""Exhibit receipt (WF-02.07 to WF-02.10).

A receipt lists the selected accepted exhibits, shows rejected ones
separately, and is completed by capturing the actual submitter's signature.
On completion the full receipt content plus the signature image is kept as an
immutable document, the exhibits become received, and the receiving staff
member takes first custody.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, documents
from app.core.errors import DomainError, InvalidTransition, NotFound
from app.core.files import FileStore, StoredFile, store_file
from app.core.ids import next_identifier
from app.core.workflow import StateMachine, Transition
from app.modules.cases import policy
from app.modules.cases import service as cases
from app.modules.cases.models import Case, Exhibit, ExhibitState, Subcase
from app.modules.custody import service as custody
from app.modules.identity.models import User
from app.modules.items.models import Item
from app.modules.receipt.models import ExceptionKind, Receipt, ReceiptItem, ReceiptState

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_SIGNATURE_BYTES = 512 * 1024
ACTIVE_STATES = (ReceiptState.DRAFT, ReceiptState.EXCEPTION, ReceiptState.COMPLETED)

RECEIPT_MACHINE = StateMachine.build(
    "receipt",
    states=[s.value for s in ReceiptState],
    initial=ReceiptState.DRAFT.value,
    transitions=[
        Transition(
            "complete",
            frozenset({ReceiptState.DRAFT}),
            ReceiptState.COMPLETED,
            policy.RECEPTION_ROLES,
        ),
        Transition(
            "record_exception",
            frozenset({ReceiptState.DRAFT}),
            ReceiptState.EXCEPTION,
            policy.RECEPTION_ROLES,
            reason_required=True,
        ),
        Transition(
            "retry",
            frozenset({ReceiptState.EXCEPTION}),
            ReceiptState.DRAFT,
            policy.RECEPTION_ROLES,
            reason_required=True,
        ),
        Transition(
            "cancel",
            frozenset({ReceiptState.DRAFT, ReceiptState.EXCEPTION}),
            ReceiptState.CANCELLED,
            policy.RECEPTION_ROLES,
            reason_required=True,
        ),
    ],
)


def open_receipt_for(session: Session, exhibit_id: uuid.UUID) -> Receipt | None:
    """The draft, exception or completed receipt that lists this exhibit, if any."""
    return session.execute(
        select(Receipt)
        .join(ReceiptItem, ReceiptItem.receipt_id == Receipt.id)
        .where(ReceiptItem.exhibit_id == exhibit_id, Receipt.state.in_(ACTIVE_STATES))
    ).scalar_one_or_none()


def get_receipt(session: Session, actor: User, receipt_id: uuid.UUID) -> Receipt:
    receipt = session.get(Receipt, receipt_id)
    if receipt is None:
        raise NotFound("Record not found")
    cases.get_subcase(session, actor, receipt.subcase_id)
    return receipt


def receipt_exhibits(session: Session, receipt: Receipt) -> list[Exhibit]:
    return list(
        session.execute(
            select(Exhibit)
            .join(ReceiptItem, ReceiptItem.exhibit_id == Exhibit.id)
            .where(ReceiptItem.receipt_id == receipt.id)
            .order_by(Exhibit.created_at)
        ).scalars()
    )


def rejected_exhibits(session: Session, subcase_id: uuid.UUID) -> list[Exhibit]:
    return list(
        session.execute(
            select(Exhibit)
            .where(Exhibit.subcase_id == subcase_id, Exhibit.state == ExhibitState.REJECTED)
            .order_by(Exhibit.created_at)
        ).scalars()
    )


def prepare_receipt(
    session: Session,
    *,
    actor: User,
    subcase_id: uuid.UUID,
    exhibit_ids: list[uuid.UUID],
    actual_submitter_name: str | None = None,
) -> Receipt:
    policy.require_roles(actor, policy.RECEPTION_ROLES, "prepare receipts")
    subcase = cases.get_subcase(session, actor, subcase_id)
    if not exhibit_ids:
        raise DomainError("Select at least one accepted exhibit for the receipt")
    exhibits = []
    for exhibit_id in dict.fromkeys(exhibit_ids):
        exhibit = cases.get_exhibit(session, actor, exhibit_id)
        if exhibit.subcase_id != subcase.id:
            raise DomainError("All exhibits on a receipt must belong to the same subcase")
        if exhibit.state != ExhibitState.ACCEPTED:
            raise InvalidTransition(f"Exhibit {exhibit_id} is not accepted")
        if open_receipt_for(session, exhibit.id):
            raise InvalidTransition(f"Exhibit {exhibit_id} is already on a receipt")
        exhibits.append(exhibit)

    case = session.get(Case, subcase.case_id)
    assert case is not None
    receipt = Receipt(
        receipt_number=next_identifier(session, "receipt"),
        subcase_id=subcase.id,
        state=ReceiptState.DRAFT,
        prepared_by=actor.id,
        actual_submitter_name=actual_submitter_name or case.submitter_name,
    )
    session.add(receipt)
    session.flush()
    for exhibit in exhibits:
        session.add(ReceiptItem(receipt_id=receipt.id, exhibit_id=exhibit.id))
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="receipt.prepared",
        entity_type="receipt",
        entity_id=receipt.id,
        after={
            "receipt_number": receipt.receipt_number,
            "exhibit_ids": [e.id for e in exhibits],
            "actual_submitter_name": receipt.actual_submitter_name,
        },
    )
    return receipt


def _snapshot(
    session: Session, receipt: Receipt, receiver: User, completed_at: datetime
) -> dict[str, Any]:
    subcase = session.get(Subcase, receipt.subcase_id)
    assert subcase is not None
    case = session.get(Case, subcase.case_id)
    assert case is not None

    def line(e: Exhibit) -> dict[str, Any]:
        item = session.get(Item, e.id)
        return {
            "barcode": item.barcode if item else None,
            "submitter_item_ref": e.submitter_item_ref,
            "description": e.description,
            "marking": e.marking,
            "seal": e.seal,
            "description_matches": e.description_matches,
            "marking_matches": e.marking_matches,
            "seal_intact": e.seal_intact,
            "check_notes": e.check_notes,
            "rejection_reason": e.rejection_reason,
        }

    return {
        "receipt_number": receipt.receipt_number,
        "case_number": case.case_number,
        "client_reference": case.client_reference,
        "subcase_number": subcase.subcase_number,
        "investigating_officer": case.investigating_officer_name,
        "actual_submitter": receipt.actual_submitter_name,
        "receiving_staff": {"id": str(receiver.id), "name": receiver.display_name},
        "completed_at": completed_at.isoformat(),
        "accepted_exhibits": [line(e) for e in receipt_exhibits(session, receipt)],
        "rejected_exhibits": [line(e) for e in rejected_exhibits(session, subcase.id)],
    }


def complete_receipt(
    session: Session,
    *,
    actor: User,
    store: FileStore,
    receipt_id: uuid.UUID,
    signature_png: bytes,
    actual_submitter_name: str,
) -> Receipt:
    """Record the actual submitter's signature and the receiving staff member,
    and retain the signed receipt (WF-02.08, WF-02.09)."""
    policy.require_roles(actor, policy.RECEPTION_ROLES, "complete receipts")
    receipt = get_receipt(session, actor, receipt_id)
    if not actual_submitter_name.strip():
        raise DomainError("Record the name of the person handing over the exhibits")
    if not signature_png.startswith(PNG_MAGIC) or len(signature_png) > MAX_SIGNATURE_BYTES:
        raise DomainError("The signature must be a PNG image of at most 512 KB")
    exhibits = receipt_exhibits(session, receipt)
    if any(e.state != ExhibitState.ACCEPTED for e in exhibits):
        raise InvalidTransition("An exhibit on this receipt is no longer accepted")

    receipt.actual_submitter_name = actual_submitter_name.strip()
    RECEIPT_MACHINE.apply(
        session,
        receipt,
        "complete",
        actor=actor,
        data={"actual_submitter_name": receipt.actual_submitter_name},
    )
    signature: StoredFile = store_file(
        session,
        store,
        data=signature_png,
        original_name=f"{receipt.receipt_number}-submitter-signature.png",
        media_type="image/png",
        actor_id=actor.id,
    )
    receipt.signature_file_id = signature.id
    receipt.receiving_staff_id = actor.id
    receipt.completed_at = custody._now(session)

    for exhibit in exhibits:
        cases.EXHIBIT_MACHINE.apply(
            session, exhibit, "receive", actor=actor, data={"receipt_id": receipt.id}
        )
        exhibit.receipt_id = receipt.id

    version = documents.create_document(
        session,
        actor=actor,
        doc_type="exhibit_receipt",
        subject_type="receipt",
        subject_id=receipt.id,
        title=f"Exhibit receipt {receipt.receipt_number}",
        content=_snapshot(session, receipt, actor, receipt.completed_at),
        file=signature,
    )
    receipt.record_document_id = version.document_id

    items = [session.get(Item, e.id) for e in exhibits]
    custody.record_receipt(session, actor=actor, items=[i for i in items if i is not None])
    return receipt


def record_exception(
    session: Session, *, actor: User, receipt_id: uuid.UUID, kind: ExceptionKind, note: str
) -> Receipt:
    """Refusal, failed signature or another handover problem, kept for follow-up
    (WF-02.10)."""
    receipt = get_receipt(session, actor, receipt_id)
    RECEIPT_MACHINE.apply(
        session, receipt, "record_exception", actor=actor, reason=note, data={"kind": kind}
    )
    receipt.exception_kind = kind
    receipt.exception_note = note.strip()
    return receipt


def retry_receipt(session: Session, *, actor: User, receipt_id: uuid.UUID, note: str) -> Receipt:
    receipt = get_receipt(session, actor, receipt_id)
    RECEIPT_MACHINE.apply(session, receipt, "retry", actor=actor, reason=note)
    return receipt


def cancel_receipt(session: Session, *, actor: User, receipt_id: uuid.UUID, reason: str) -> Receipt:
    receipt = get_receipt(session, actor, receipt_id)
    RECEIPT_MACHINE.apply(session, receipt, "cancel", actor=actor, reason=reason)
    return receipt


def open_exceptions(session: Session, actor: User) -> list[Receipt]:
    return list(
        session.execute(
            select(Receipt)
            .join(Subcase, Subcase.id == Receipt.subcase_id)
            .where(
                Receipt.state == ReceiptState.EXCEPTION,
                Subcase.laboratory_id.in_(actor.laboratory_ids),
            )
            .order_by(Receipt.created_at)
        ).scalars()
    )


def list_receipts(session: Session, subcase_id: uuid.UUID) -> list[Receipt]:
    return list(
        session.execute(
            select(Receipt).where(Receipt.subcase_id == subcase_id).order_by(Receipt.created_at)
        ).scalars()
    )

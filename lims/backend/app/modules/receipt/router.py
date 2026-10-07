import base64
import binascii
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.errors import DomainError, NotFound
from app.core.files import FileStore, get_file_store, read_file
from app.modules.cases import service as cases_service
from app.modules.cases.router import exhibit_out, person
from app.modules.cases.schemas import ExhibitOut, Person
from app.modules.receipt import service
from app.modules.receipt.models import ExceptionKind, Receipt, ReceiptState

router = APIRouter(tags=["receipts"])
Db = Annotated[Session, Depends(get_db)]
Store = Annotated[FileStore, Depends(get_file_store)]


class ReceiptPrepare(BaseModel):
    exhibit_ids: list[uuid.UUID] = Field(min_length=1)
    actual_submitter_name: str | None = None


class ReceiptComplete(BaseModel):
    actual_submitter_name: str = Field(min_length=1, max_length=200)
    signature_png_base64: str = Field(min_length=8)


class ExceptionIn(BaseModel):
    kind: ExceptionKind
    note: str = Field(min_length=3)


class NoteIn(BaseModel):
    note: str = Field(min_length=3)


class ReceiptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_number: str
    subcase_id: uuid.UUID
    state: ReceiptState
    created_at: datetime
    completed_at: datetime | None
    exception_kind: ExceptionKind | None
    exception_note: str | None


class ReceiptOut(ReceiptSummary):
    actual_submitter_name: str | None
    prepared_by: Person | None
    receiving_staff: Person | None
    has_signature: bool
    record_document_id: uuid.UUID | None
    accepted_exhibits: list[ExhibitOut]
    rejected_exhibits: list[ExhibitOut]


def receipt_out(db: Session, receipt: Receipt) -> ReceiptOut:
    data: dict[str, Any] = ReceiptSummary.model_validate(receipt).model_dump()
    return ReceiptOut(
        **data,
        actual_submitter_name=receipt.actual_submitter_name,
        prepared_by=person(db, receipt.prepared_by),
        receiving_staff=person(db, receipt.receiving_staff_id),
        has_signature=receipt.signature_file_id is not None,
        record_document_id=receipt.record_document_id,
        accepted_exhibits=[exhibit_out(db, e) for e in service.receipt_exhibits(db, receipt)],
        rejected_exhibits=[
            exhibit_out(db, e) for e in service.rejected_exhibits(db, receipt.subcase_id)
        ],
    )


@router.get("/subcases/{subcase_id}/receipts", response_model=list[ReceiptSummary])
def receipts(subcase_id: uuid.UUID, db: Db, user: CurrentUser) -> list:
    cases_service.get_subcase(db, user, subcase_id)
    return service.list_receipts(db, subcase_id)


@router.post("/subcases/{subcase_id}/receipts", response_model=ReceiptOut, status_code=201)
def prepare(subcase_id: uuid.UUID, body: ReceiptPrepare, db: Db, user: CurrentUser) -> ReceiptOut:
    receipt = service.prepare_receipt(
        db,
        actor=user,
        subcase_id=subcase_id,
        exhibit_ids=body.exhibit_ids,
        actual_submitter_name=body.actual_submitter_name,
    )
    return receipt_out(db, receipt)


@router.get("/receipts/{receipt_id}", response_model=ReceiptOut)
def get(receipt_id: uuid.UUID, db: Db, user: CurrentUser) -> ReceiptOut:
    return receipt_out(db, service.get_receipt(db, user, receipt_id))


@router.post("/receipts/{receipt_id}/complete", response_model=ReceiptOut)
def complete(
    receipt_id: uuid.UUID, body: ReceiptComplete, db: Db, user: CurrentUser, store: Store
) -> ReceiptOut:
    encoded = body.signature_png_base64.split(",", 1)[-1]  # accept a data: URL too
    try:
        signature = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise DomainError("The signature is not valid base64") from exc
    receipt = service.complete_receipt(
        db,
        actor=user,
        store=store,
        receipt_id=receipt_id,
        signature_png=signature,
        actual_submitter_name=body.actual_submitter_name,
    )
    return receipt_out(db, receipt)


@router.get("/receipts/{receipt_id}/signature")
def signature(receipt_id: uuid.UUID, db: Db, user: CurrentUser, store: Store) -> Response:
    receipt = service.get_receipt(db, user, receipt_id)
    if receipt.signature_file_id is None:
        raise NotFound("No signature recorded")
    record, data = read_file(db, store, receipt.signature_file_id)
    return Response(content=data, media_type=record.media_type)


@router.post("/receipts/{receipt_id}/exception", response_model=ReceiptOut)
def exception(receipt_id: uuid.UUID, body: ExceptionIn, db: Db, user: CurrentUser) -> ReceiptOut:
    receipt = service.record_exception(
        db, actor=user, receipt_id=receipt_id, kind=body.kind, note=body.note
    )
    return receipt_out(db, receipt)


@router.post("/receipts/{receipt_id}/retry", response_model=ReceiptOut)
def retry(receipt_id: uuid.UUID, body: NoteIn, db: Db, user: CurrentUser) -> ReceiptOut:
    return receipt_out(
        db, service.retry_receipt(db, actor=user, receipt_id=receipt_id, note=body.note)
    )


@router.post("/receipts/{receipt_id}/cancel", response_model=ReceiptOut)
def cancel(receipt_id: uuid.UUID, body: NoteIn, db: Db, user: CurrentUser) -> ReceiptOut:
    return receipt_out(
        db, service.cancel_receipt(db, actor=user, receipt_id=receipt_id, reason=body.note)
    )

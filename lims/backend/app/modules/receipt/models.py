import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPk


class ReceiptState(StrEnum):
    DRAFT = "draft"  # prepared, awaiting the submitter's signature
    COMPLETED = "completed"  # signed; exhibits received
    EXCEPTION = "exception"  # refusal, failed signature or other handover problem
    CANCELLED = "cancelled"


class ExceptionKind(StrEnum):
    SUBMITTER_REFUSED = "submitter_refused"
    SIGNATURE_FAILED = "signature_failed"
    HANDOVER_OTHER = "handover_other"


class Receipt(UUIDPk, CreatedAt, Base):
    """Receipt for the selected accepted exhibits (WF-02.07 to WF-02.10)."""

    __tablename__ = "receipt"

    receipt_number: Mapped[str] = mapped_column(String(30), unique=True)
    subcase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subcase.id"), index=True)
    state: Mapped[ReceiptState] = mapped_column(
        Enum(ReceiptState, name="receipt_state", values_callable=lambda e: [m.value for m in e]),
        default=ReceiptState.DRAFT,
    )
    prepared_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    # The person who physically hands over the exhibits; may differ from the
    # submitter named at registration (WF-02.08).
    actual_submitter_name: Mapped[str | None] = mapped_column(String(200))
    receiving_staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    signature_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_file.id"))
    record_document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exception_kind: Mapped[ExceptionKind | None] = mapped_column(
        Enum(
            ExceptionKind, name="receipt_exception", values_callable=lambda e: [m.value for m in e]
        )
    )
    exception_note: Mapped[str | None] = mapped_column(Text)


class ReceiptItem(Base):
    __tablename__ = "receipt_item"
    __table_args__ = (UniqueConstraint("receipt_id", "exhibit_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receipt.id"), index=True)
    exhibit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exhibit.id"), index=True)

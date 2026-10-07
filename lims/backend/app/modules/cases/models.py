import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPk


def _enum(cls: type[StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class SubmissionSource(StrEnum):
    PAPER = "paper"
    ELECTRONIC = "electronic"


class CaseState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Case(UUIDPk, CreatedAt, Base):
    """The submitting agency's case as registered by the laboratory (WF-02.01, WF-02.02)."""

    __tablename__ = "case"

    case_number: Mapped[str] = mapped_column(String(30), unique=True)
    laboratory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("laboratory.id"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"))
    client_reference: Mapped[str] = mapped_column(String(100))
    source: Mapped[SubmissionSource] = mapped_column(_enum(SubmissionSource, "submission_source"))
    submission_reference: Mapped[str | None] = mapped_column(String(100))
    submitter_name: Mapped[str] = mapped_column(String(200))
    submitter_contact: Mapped[str | None] = mapped_column(String(300))
    investigating_officer_name: Mapped[str] = mapped_column(String(200))
    investigating_officer_contact: Mapped[str | None] = mapped_column(String(300))
    case_information: Mapped[str | None] = mapped_column(Text)
    state: Mapped[CaseState] = mapped_column(_enum(CaseState, "case_state"), default=CaseState.OPEN)
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))


class SubcaseState(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Subcase(UUIDPk, CreatedAt, Base):
    """The laboratory's own unit of work within a case (WF-02.03)."""

    __tablename__ = "subcase"

    subcase_number: Mapped[str] = mapped_column(String(30), unique=True)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("case.id"), index=True)
    laboratory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("laboratory.id"))
    state: Mapped[SubcaseState] = mapped_column(
        _enum(SubcaseState, "subcase_state"), default=SubcaseState.OPEN
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))


class ExhibitState(StrEnum):
    SUBMITTED = "submitted"  # recorded from the submission, not yet checked
    ACCEPTED = "accepted"  # checked and accepted, awaiting receipt
    REJECTED = "rejected"
    RECEIVED = "received"  # on a completed, signed receipt


class Exhibit(CreatedAt, Base):
    """An exhibit submitted for examination. Shares its id and barcode with its Item."""

    __tablename__ = "exhibit"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("item.id"), primary_key=True)
    subcase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subcase.id"), index=True)
    submitter_item_ref: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    marking: Mapped[str | None] = mapped_column(String(300))
    seal: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[ExhibitState] = mapped_column(
        _enum(ExhibitState, "exhibit_state"), default=ExhibitState.SUBMITTED
    )
    description_matches: Mapped[bool | None] = mapped_column(Boolean)
    marking_matches: Mapped[bool | None] = mapped_column(Boolean)
    seal_intact: Mapped[bool | None] = mapped_column(Boolean)
    check_notes: Mapped[str | None] = mapped_column(Text)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    receipt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("receipt.id"))
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))

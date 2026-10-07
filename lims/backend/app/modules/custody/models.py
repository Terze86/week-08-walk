import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPk, append_only


def _enum(cls: type[StrEnum], name: str) -> Enum:
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class MovementKind(StrEnum):
    RECEIPT = "receipt"  # first custody, on completion of a signed receipt
    MOVE = "move"  # retrieve, store, batch move
    HANDOVER = "handover"  # accepted by the receiving person
    CORRECTION = "correction"  # authorised replacement of an earlier entry


@append_only
class CustodyMovement(UUIDPk, Base):
    """One custody change for one item. Never edited: a wrong entry is replaced
    by an authorised correction movement that points at it (WF-03.10)."""

    __tablename__ = "custody_movement"
    __table_args__ = (
        CheckConstraint(
            "to_person_id IS NOT NULL OR to_location_id IS NOT NULL", name="has_destination"
        ),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("item.id"), index=True)
    kind: Mapped[MovementKind] = mapped_column(_enum(MovementKind, "movement_kind"))
    from_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("location.id"))
    to_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("location.id"))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    group_id: Mapped[uuid.UUID] = mapped_column(index=True)  # shared by a batch movement
    corrects_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("custody_movement.id")
    )
    note: Mapped[str | None] = mapped_column(Text)


class CorrectionState(StrEnum):
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    DECLINED = "declined"


class CustodyCorrection(UUIDPk, CreatedAt, Base):
    __tablename__ = "custody_correction"

    movement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("custody_movement.id"), index=True)
    state: Mapped[CorrectionState] = mapped_column(
        _enum(CorrectionState, "correction_state"), default=CorrectionState.REQUESTED
    )
    reason: Mapped[str] = mapped_column(Text)
    to_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("location.id"))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
    correction_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("custody_movement.id")
    )


class HandoverItemState(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class Handover(UUIDPk, CreatedAt, Base):
    """Person-to-person transfer, completed only when the designated receiver
    signs in and accepts the items (WF-03.08)."""

    __tablename__ = "handover"

    from_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    to_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), index=True)
    note: Mapped[str | None] = mapped_column(String(500))


class HandoverItem(UUIDPk, Base):
    __tablename__ = "handover_item"

    handover_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("handover.id"), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("item.id"), index=True)
    state: Mapped[HandoverItemState] = mapped_column(
        _enum(HandoverItemState, "handover_item_state"), default=HandoverItemState.PENDING
    )
    movement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("custody_movement.id"))

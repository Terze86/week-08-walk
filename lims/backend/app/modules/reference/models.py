import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPk


class Client(UUIDPk, CreatedAt, Base):
    """A submitting agency (e.g. a police division)."""

    __tablename__ = "client"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LocationKind(StrEnum):
    STORAGE = "storage"
    BENCH = "bench"
    INSTRUMENT = "instrument"
    TRANSIT = "transit"
    DISPOSAL = "disposal"


class Location(UUIDPk, CreatedAt, Base):
    """A place where items are kept; its code is printed as a scannable barcode."""

    __tablename__ = "location"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[LocationKind] = mapped_column(
        Enum(LocationKind, name="location_kind", values_callable=lambda e: [m.value for m in e])
    )
    laboratory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("laboratory.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

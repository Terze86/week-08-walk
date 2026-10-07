"""Every physical thing the laboratory tracks is an Item: exhibits now, and
samples, extracts and amplified products later. One table gives one barcode
namespace, one custody history mechanism and a lineage graph (parent_id) from
exhibit to sample to extract to amplified product (WF-04.03, WF-07.11, WF-09.07).
"""

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, CreatedAt, UUIDPk


class ItemKind(StrEnum):
    EXHIBIT = "exhibit"
    SAMPLE = "sample"
    MATERIAL = "material"


class Item(UUIDPk, CreatedAt, Base):
    __tablename__ = "item"

    barcode: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[ItemKind] = mapped_column(
        Enum(ItemKind, name="item_kind", values_callable=lambda e: [m.value for m in e])
    )
    subcase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subcase.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item.id"))
    label: Mapped[str] = mapped_column(String(300))

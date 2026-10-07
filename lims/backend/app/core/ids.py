"""Human-readable, gap-free identifiers for cases, exhibits, samples and batches.

The identifier doubles as the barcode value (Code 128), as in WF-02.04 and
WF-04.04. The formats below are placeholders until the laboratory confirms its
own numbering scheme.
"""

from datetime import date

from sqlalchemy import Integer, String, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base

ID_FORMATS: dict[str, str] = {
    "case": "C{year}-{seq:06d}",
    "subcase": "LAB{year}-{seq:06d}",
    "exhibit": "EX{year}-{seq:07d}",
    "sample": "S{year}-{seq:07d}",
    "material": "M{year}-{seq:07d}",
    "batch": "B{year}-{seq:05d}",
    "receipt": "R{year}-{seq:06d}",
    "report": "RPT{year}-{seq:06d}",
    "codis_request": "CR{year}-{seq:05d}",
}


class IdSequence(Base):
    __tablename__ = "id_sequence"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    period: Mapped[str] = mapped_column(String(10), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer)


def next_identifier(session: Session, name: str, *, today: date | None = None) -> str:
    """Allocate the next identifier atomically. Rolled-back transactions do not
    consume a number, because the counter row update rolls back with them."""
    fmt = ID_FORMATS[name]
    year = (today or date.today()).year
    seq = session.execute(
        text(
            "INSERT INTO id_sequence (name, period, last_value) VALUES (:n, :p, 1) "
            "ON CONFLICT (name, period) DO UPDATE SET last_value = id_sequence.last_value + 1 "
            "RETURNING last_value"
        ),
        {"n": name, "p": str(year)},
    ).scalar_one()
    return fmt.format(year=year, seq=seq)

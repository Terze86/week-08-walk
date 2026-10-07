from datetime import date

from sqlalchemy.orm import Session

from app.core.ids import ID_FORMATS, next_identifier


def test_identifiers_are_sequential_per_type_and_year(db: Session) -> None:
    d = date(2026, 3, 1)
    assert next_identifier(db, "exhibit", today=d) == "EX2026-0000001"
    assert next_identifier(db, "exhibit", today=d) == "EX2026-0000002"
    assert next_identifier(db, "sample", today=d) == "S2026-0000001"
    assert next_identifier(db, "exhibit", today=date(2027, 1, 1)) == "EX2027-0000001"


def test_every_format_renders() -> None:
    for fmt in ID_FORMATS.values():
        assert fmt.format(year=2026, seq=1)

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core import documents as docs
from app.core.documents import ReauthProof, SignatureMeaning
from app.core.errors import DomainError, InvalidTransition, PermissionDenied, ReasonRequired


def fresh(user) -> ReauthProof:
    return ReauthProof(user.id, datetime.now(UTC))


@pytest.fixture
def v1(db: Session, staff):
    return docs.create_document(
        db,
        actor=staff["slo1"],
        doc_type="exhibit_documentation",
        subject_type="exhibit",
        subject_id="EX2026-0000001",
        title="Exhibit documentation",
        content={"narrative": "Blue cotton shirt, stain at left cuff."},
    )


def test_both_signatures_apply_to_the_same_version(db: Session, staff, v1) -> None:
    docs.sign(
        db,
        actor=staff["slo1"],
        version=v1,
        meaning=SignatureMeaning.COMPLETED,
        reauth=fresh(staff["slo1"]),
    )
    docs.sign(
        db,
        actor=staff["cs1"],
        version=v1,
        meaning=SignatureMeaning.REVIEWED,
        reauth=fresh(staff["cs1"]),
    )
    assert docs.has_signature(db, v1, SignatureMeaning.COMPLETED)
    assert docs.has_signature(db, v1, SignatureMeaning.REVIEWED, signer_id=staff["cs1"].id)
    sigs = docs.signatures_for(db, v1)
    assert {s.content_hash for s in sigs} == {v1.content_hash}


def test_correction_creates_new_version_and_signoffs_must_be_repeated(
    db: Session, staff, v1
) -> None:
    docs.sign(
        db,
        actor=staff["slo1"],
        version=v1,
        meaning=SignatureMeaning.COMPLETED,
        reauth=fresh(staff["slo1"]),
    )
    with pytest.raises(ReasonRequired):
        docs.new_version(
            db, actor=staff["slo1"], document_id=v1.document_id, content={}, reason=" "
        )
    v2 = docs.new_version(
        db,
        actor=staff["slo1"],
        document_id=v1.document_id,
        content={"narrative": "Blue cotton shirt, stain at right cuff."},
        reason="Cuff side recorded incorrectly",
    )
    assert v2.version_no == 2 and v2.content_hash != v1.content_hash
    assert not docs.has_signature(db, v2, SignatureMeaning.COMPLETED)
    # The earlier version and its signature are retained...
    assert docs.has_signature(db, v1, SignatureMeaning.COMPLETED)
    # ...but nobody can sign the superseded version any more.
    with pytest.raises(InvalidTransition):
        docs.sign(
            db,
            actor=staff["cs1"],
            version=v1,
            meaning=SignatureMeaning.REVIEWED,
            reauth=fresh(staff["cs1"]),
        )


def test_signing_requires_fresh_reauthentication_by_the_signer(db: Session, staff, v1) -> None:
    stale = ReauthProof(staff["slo1"].id, datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(PermissionDenied):
        docs.sign(
            db, actor=staff["slo1"], version=v1, meaning=SignatureMeaning.COMPLETED, reauth=stale
        )
    with pytest.raises(PermissionDenied):
        docs.sign(
            db,
            actor=staff["slo1"],
            version=v1,
            meaning=SignatureMeaning.COMPLETED,
            reauth=fresh(staff["cs1"]),
        )


def test_duplicate_signature_is_rejected(db: Session, staff, v1) -> None:
    docs.sign(
        db,
        actor=staff["slo1"],
        version=v1,
        meaning=SignatureMeaning.COMPLETED,
        reauth=fresh(staff["slo1"]),
    )
    with pytest.raises(DomainError):
        docs.sign(
            db,
            actor=staff["slo1"],
            version=v1,
            meaning=SignatureMeaning.COMPLETED,
            reauth=fresh(staff["slo1"]),
        )


def test_signature_records_meaning_statement(db: Session, staff, v1) -> None:
    sig = docs.sign(
        db,
        actor=staff["cs1"],
        version=v1,
        meaning=SignatureMeaning.REVIEWED,
        reauth=fresh(staff["cs1"]),
    )
    assert sig.statement == docs.SIGNATURE_STATEMENTS[SignatureMeaning.REVIEWED]
    assert set(docs.SIGNATURE_STATEMENTS) == set(SignatureMeaning)

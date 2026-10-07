"""Versioned documents and e-signatures bound to an exact version.

A signature records the content hash of the version it was applied to. Editing
a document always creates a new version, so earlier signatures never carry over:
the applicable sign-offs must be repeated on the new version (WF-05.05,
WF-05.06, WF-17.05, WF-17.07, WF-17.10).
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core import audit
from app.core.config import get_settings
from app.core.db import Base, CreatedAt, UUIDPk, append_only
from app.core.errors import (
    DomainError,
    IntegrityFailure,
    InvalidTransition,
    NotFound,
    PermissionDenied,
    ReasonRequired,
)
from app.core.files import StoredFile
from app.modules.identity.models import User


class SignatureMeaning(StrEnum):
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    AUTHORIZED = "authorized"
    INDEPENDENT_CHECK = "independent_check"
    ADMINISTRATIVE_REVIEW = "administrative_review"
    TECHNICAL_REVIEW = "technical_review"
    FINAL_SIGNOFF = "final_signoff"


SIGNATURE_STATEMENTS = {
    SignatureMeaning.COMPLETED: "I completed this record and confirm it is accurate.",
    SignatureMeaning.REVIEWED: "I reviewed this record.",
    SignatureMeaning.APPROVED: "I approve this record.",
    SignatureMeaning.AUTHORIZED: "I authorize the work described in this record.",
    SignatureMeaning.INDEPENDENT_CHECK: "I independently checked this record.",
    SignatureMeaning.ADMINISTRATIVE_REVIEW: "I performed the administrative review.",
    SignatureMeaning.TECHNICAL_REVIEW: "I performed the technical review.",
    SignatureMeaning.FINAL_SIGNOFF: "I give final sign-off for issue of this version.",
}


@dataclass(frozen=True)
class ReauthProof:
    """Evidence that the signer re-authenticated just before signing."""

    user_id: uuid.UUID
    authenticated_at: datetime


@append_only
class Document(UUIDPk, CreatedAt, Base):
    __tablename__ = "document"

    doc_type: Mapped[str] = mapped_column(String(100))
    subject_type: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))


@append_only
class DocumentVersion(UUIDPk, CreatedAt, Base):
    __tablename__ = "document_version"
    __table_args__ = (UniqueConstraint("document_id", "version_no"),)

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_file.id"))
    content_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    change_reason: Mapped[str | None] = mapped_column(Text)


@append_only
class Signature(UUIDPk, Base):
    __tablename__ = "signature"
    __table_args__ = (UniqueConstraint("document_version_id", "signer_id", "meaning"),)

    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_version.id"), index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64))
    signer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    meaning: Mapped[SignatureMeaning] = mapped_column(
        Enum(
            SignatureMeaning,
            name="signature_meaning",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    statement: Mapped[str] = mapped_column(Text)
    reauthenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def compute_content_hash(content: dict[str, Any], file: StoredFile | None) -> str:
    canonical = json.dumps(
        {"content": content, "file_sha256": file.sha256 if file else None},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _normalise(content: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(json.dumps(content, default=str))
    return result


def create_document(
    session: Session,
    *,
    actor: User,
    doc_type: str,
    subject_type: str,
    subject_id: object,
    title: str,
    content: dict[str, Any],
    file: StoredFile | None = None,
) -> DocumentVersion:
    doc = Document(
        doc_type=doc_type,
        subject_type=subject_type,
        subject_id=str(subject_id),
        title=title,
        created_by=actor.id,
    )
    session.add(doc)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="document.created",
        entity_type="document",
        entity_id=doc.id,
        after={"doc_type": doc_type, "subject": f"{subject_type}:{subject_id}", "title": title},
    )
    return _add_version(session, actor, doc, 1, content, file, None)


def new_version(
    session: Session,
    *,
    actor: User,
    document_id: uuid.UUID,
    content: dict[str, Any],
    reason: str,
    file: StoredFile | None = None,
) -> DocumentVersion:
    if not reason or not reason.strip():
        raise ReasonRequired("A new document version requires a reason for the change")
    doc = session.get(Document, document_id)
    if doc is None:
        raise NotFound("Document not found")
    current = latest_version(session, document_id)
    return _add_version(session, actor, doc, current.version_no + 1, content, file, reason.strip())


def _add_version(
    session: Session,
    actor: User,
    doc: Document,
    version_no: int,
    content: dict[str, Any],
    file: StoredFile | None,
    reason: str | None,
) -> DocumentVersion:
    content = _normalise(content)
    version = DocumentVersion(
        document_id=doc.id,
        version_no=version_no,
        content=content,
        file_id=file.id if file else None,
        content_hash=compute_content_hash(content, file),
        created_by=actor.id,
        change_reason=reason,
    )
    session.add(version)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="document.version_created",
        entity_type="document",
        entity_id=doc.id,
        reason=reason,
        after={"version_no": version_no, "content_hash": version.content_hash},
    )
    return version


def latest_version(session: Session, document_id: uuid.UUID) -> DocumentVersion:
    version = session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    ).scalar_one_or_none()
    if version is None:
        raise NotFound("Document has no versions")
    return version


def verify_version(session: Session, version: DocumentVersion) -> None:
    file = session.get(StoredFile, version.file_id) if version.file_id else None
    if compute_content_hash(version.content, file) != version.content_hash:
        raise IntegrityFailure(f"Document version {version.id} failed its integrity check")


def sign(
    session: Session,
    *,
    actor: User,
    version: DocumentVersion,
    meaning: SignatureMeaning,
    reauth: ReauthProof,
) -> Signature:
    if not actor.is_active:
        raise PermissionDenied("Account is disabled")
    max_age = get_settings().signature_reauth_max_age_seconds
    age = (datetime.now(UTC) - reauth.authenticated_at).total_seconds()
    if reauth.user_id != actor.id or age > max_age or age < -60:
        raise PermissionDenied("Signing requires you to re-authenticate first")
    if latest_version(session, version.document_id).id != version.id:
        raise InvalidTransition("This version has been superseded; sign the current version")
    verify_version(session, version)
    if has_signature(session, version, meaning, signer_id=actor.id):
        raise DomainError("You have already signed this version with that meaning")

    signature = Signature(
        document_version_id=version.id,
        content_hash=version.content_hash,
        signer_id=actor.id,
        meaning=meaning,
        statement=SIGNATURE_STATEMENTS[meaning],
        reauthenticated_at=reauth.authenticated_at,
    )
    session.add(signature)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="document.signed",
        entity_type="document",
        entity_id=version.document_id,
        after={
            "version_no": version.version_no,
            "meaning": meaning.value,
            "content_hash": version.content_hash,
        },
    )
    return signature


def signatures_for(session: Session, version: DocumentVersion) -> list[Signature]:
    return list(
        session.execute(
            select(Signature)
            .where(Signature.document_version_id == version.id)
            .order_by(Signature.signed_at)
        ).scalars()
    )


def has_signature(
    session: Session,
    version: DocumentVersion,
    meaning: SignatureMeaning,
    *,
    signer_id: uuid.UUID | None = None,
) -> bool:
    query = select(Signature.id).where(
        Signature.document_version_id == version.id,
        Signature.meaning == meaning,
        Signature.content_hash == version.content_hash,
    )
    if signer_id is not None:
        query = query.where(Signature.signer_id == signer_id)
    return session.execute(query.limit(1)).first() is not None

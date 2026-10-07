"""Record-level access grants.

Roles decide which workspace a person uses; grants decide which records they
see inside it (WF-01.05). Assignments (Case Scientist ↔ subcase, Screening Lab
Officer ↔ exhibit examination) and CODIS shares (a CODIS Scientist ↔ one
request and the exact profile versions and files in it, WF-01.06) are both
grants. Revoking a grant keeps the row and its history.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core import audit
from app.core.db import Base, UUIDPk
from app.core.errors import DomainError, NotFound, ReasonRequired


class GrantKind(StrEnum):
    ASSIGNMENT = "assignment"
    CODIS_SHARE = "codis_share"


class AccessGrant(UUIDPk, Base):
    __tablename__ = "access_grant"
    __table_args__ = (
        Index("ix_access_grant_lookup", "user_id", "entity_type", "entity_id"),
        Index(
            "uq_access_grant_active",
            "user_id",
            "entity_type",
            "entity_id",
            "kind",
            unique=True,
            postgresql_where="revoked_at IS NULL",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    kind: Mapped[GrantKind] = mapped_column(
        Enum(GrantKind, name="grant_kind", values_callable=lambda e: [m.value for m in e])
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(Text)


def grant(
    session: Session,
    *,
    actor_id: uuid.UUID,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: object,
    kind: GrantKind,
) -> AccessGrant:
    if has_grant(session, user_id, entity_type, entity_id, kinds=(kind,)):
        raise DomainError("This access is already granted")
    row = AccessGrant(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        kind=kind,
        granted_by=actor_id,
    )
    session.add(row)
    session.flush()
    audit.record(
        session,
        actor_id=actor_id,
        action="access.granted",
        entity_type=entity_type,
        entity_id=entity_id,
        after={"user_id": str(user_id), "kind": kind.value, "grant_id": str(row.id)},
    )
    return row


def revoke(session: Session, *, actor_id: uuid.UUID, grant_id: uuid.UUID, reason: str) -> None:
    if not reason or not reason.strip():
        raise ReasonRequired("Revoking access requires a reason")
    row = session.get(AccessGrant, grant_id)
    if row is None or row.revoked_at is not None:
        raise NotFound("Active grant not found")
    row.revoked_by = actor_id
    row.revoked_at = func.now()
    row.revoke_reason = reason.strip()
    session.flush()
    audit.record(
        session,
        actor_id=actor_id,
        action="access.revoked",
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        reason=reason.strip(),
        before={"user_id": str(row.user_id), "kind": row.kind.value, "grant_id": str(row.id)},
    )


def has_grant(
    session: Session,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: object,
    *,
    kinds: tuple[GrantKind, ...] = tuple(GrantKind),
) -> bool:
    return (
        session.execute(
            select(AccessGrant.id)
            .where(
                AccessGrant.user_id == user_id,
                AccessGrant.entity_type == entity_type,
                AccessGrant.entity_id == str(entity_id),
                AccessGrant.kind.in_(kinds),
                AccessGrant.revoked_at.is_(None),
            )
            .limit(1)
        ).first()
        is not None
    )


def granted_entity_ids(
    session: Session, user_id: uuid.UUID, entity_type: str, *, kinds: tuple[GrantKind, ...]
) -> set[str]:
    return set(
        session.execute(
            select(AccessGrant.entity_id).where(
                AccessGrant.user_id == user_id,
                AccessGrant.entity_type == entity_type,
                AccessGrant.kind.in_(kinds),
                AccessGrant.revoked_at.is_(None),
            )
        ).scalars()
    )

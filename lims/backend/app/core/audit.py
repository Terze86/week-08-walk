"""Append-only, hash-chained audit trail (WF-19.04, WF-19.06).

Every workflow action, correction and change writes one AuditEvent in the same
transaction as the change itself. Each event stores the SHA-256 of the previous
event, so any edit or deletion made outside the application (which the
database trigger already forbids) is also detectable by `verify_chain`.
"""

import hashlib
import json
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base, append_only

GENESIS_HASH = "0" * 64
# Arbitrary constant key for the advisory lock that serialises chain appends.
_CHAIN_LOCK_KEY = 0x4C494D53  # "LIMS"

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


@append_only
class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _event_hash(event: AuditEvent) -> str:
    payload = _canonical(
        {
            "prev": event.prev_hash,
            "at": event.occurred_at.astimezone(UTC).isoformat(),
            "actor": str(event.actor_id) if event.actor_id else None,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "reason": event.reason,
            "before": event.before,
            "after": event.after,
            "request_id": event.request_id,
        }
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _jsonable(value: dict[str, Any] | None) -> dict[str, Any] | None:
    # Round-trip through JSON so the stored value hashes identically on re-read.
    return None if value is None else json.loads(_canonical(value))


def record(
    session: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: object,
    reason: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append one audit event in the caller's transaction."""
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _CHAIN_LOCK_KEY})
    prev = session.execute(
        select(AuditEvent.hash).order_by(AuditEvent.id.desc()).limit(1)
    ).scalar_one_or_none()
    occurred_at = session.execute(text("SELECT clock_timestamp()")).scalar_one()

    event = AuditEvent(
        occurred_at=occurred_at,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        reason=reason,
        before=_jsonable(before),
        after=_jsonable(after),
        request_id=request_id_var.get(),
        prev_hash=prev or GENESIS_HASH,
    )
    event.hash = _event_hash(event)
    session.add(event)
    session.flush()
    return event


def verify_chain(session: Session) -> list[int]:
    """Return ids of events whose hash or link to the previous event is broken."""
    broken: list[int] = []
    expected_prev = GENESIS_HASH
    for event in session.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars():
        if event.prev_hash != expected_prev or event.hash != _event_hash(event):
            broken.append(event.id)
        expected_prev = event.hash
    return broken


def history(session: Session, entity_type: str, entity_id: object) -> list[AuditEvent]:
    return list(
        session.execute(
            select(AuditEvent)
            .where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == str(entity_id))
            .order_by(AuditEvent.id)
        ).scalars()
    )

"""Postgres-backed job queue for supporting tasks such as label printing and
report delivery. Failed jobs stay visible to the LIMS Admin, who records a
retry or a resolution with a reason (WF-19.03).
"""

import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core import audit
from app.core.db import Base, CreatedAt, UUIDPk
from app.core.errors import DomainError, NotFound, ReasonRequired


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RESOLVED = "resolved"  # failed, then closed by an admin without a retry


class Job(UUIDPk, CreatedAt, Base):
    __tablename__ = "job"

    kind: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.QUEUED,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


Handler = Callable[[Session, dict[str, Any]], None]
_HANDLERS: dict[str, Handler] = {}


def job_handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        _HANDLERS[kind] = fn
        return fn

    return register


def enqueue(
    session: Session,
    kind: str,
    payload: dict[str, Any],
    *,
    requested_by: uuid.UUID | None,
    max_attempts: int = 3,
) -> Job:
    if kind not in _HANDLERS:
        raise DomainError(f"No handler registered for job kind {kind!r}")
    job = Job(kind=kind, payload=payload, requested_by=requested_by, max_attempts=max_attempts)
    session.add(job)
    session.flush()
    return job


def run_next(session: Session) -> Job | None:
    """Claim and run one due job. The caller commits. Returns None when idle."""
    job = session.execute(
        select(Job)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= func.now())
        .order_by(Job.run_after)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if job is None:
        return None

    job.attempts += 1
    try:
        with session.begin_nested():
            _HANDLERS[job.kind](session, job.payload)
    except Exception:
        job.last_error = traceback.format_exc(limit=5)
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.FAILED
            audit.record(
                session,
                actor_id=None,
                action="job.failed",
                entity_type="job",
                entity_id=job.id,
                after={"kind": job.kind, "attempts": job.attempts},
            )
        else:
            job.run_after = func.now() + timedelta(seconds=30 * 2**job.attempts)
    else:
        job.status = JobStatus.SUCCEEDED
        job.last_error = None
    session.flush()
    return job


def _failed_job(session: Session, job_id: uuid.UUID) -> Job:
    job = session.get(Job, job_id)
    if job is None or job.status != JobStatus.FAILED:
        raise NotFound("Failed job not found")
    return job


def retry_failed(session: Session, *, actor_id: uuid.UUID, job_id: uuid.UUID, reason: str) -> Job:
    if not reason or not reason.strip():
        raise ReasonRequired("Retrying a failed job requires a reason")
    job = _failed_job(session, job_id)
    job.status = JobStatus.QUEUED
    job.attempts = 0
    job.run_after = func.now()
    audit.record(
        session,
        actor_id=actor_id,
        action="job.retried",
        entity_type="job",
        entity_id=job.id,
        reason=reason.strip(),
    )
    return job


def resolve_failed(
    session: Session, *, actor_id: uuid.UUID, job_id: uuid.UUID, resolution: str
) -> Job:
    if not resolution or not resolution.strip():
        raise ReasonRequired("Closing a failed job requires a resolution note")
    job = _failed_job(session, job_id)
    job.status = JobStatus.RESOLVED
    job.resolution_note = resolution.strip()
    audit.record(
        session,
        actor_id=actor_id,
        action="job.resolved",
        entity_type="job",
        entity_id=job.id,
        reason=resolution.strip(),
    )
    return job

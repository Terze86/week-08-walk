"""Administration and quality support (WF-19.03, WF-19.04)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit, jobs
from app.core.auth import require_roles
from app.core.db import get_db
from app.modules.identity.models import Role, User

router = APIRouter(prefix="/admin", tags=["admin"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(Role.LIMS_ADMIN))]


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str
    reason: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class ChainStatus(BaseModel):
    intact: bool
    broken_event_ids: list[int]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    status: jobs.JobStatus
    attempts: int
    last_error: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class ReasonBody(BaseModel):
    reason: str = Field(min_length=3)


@router.get("/audit", response_model=list[AuditEventOut])
def audit_events(
    db: Db,
    _: Admin,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    before_id: int | None = None,
    limit: Annotated[int, Query(le=500)] = 100,
) -> list[audit.AuditEvent]:
    query = select(audit.AuditEvent).order_by(audit.AuditEvent.id.desc()).limit(limit)
    if entity_type:
        query = query.where(audit.AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(audit.AuditEvent.entity_id == entity_id)
    if action:
        query = query.where(audit.AuditEvent.action == action)
    if before_id:
        query = query.where(audit.AuditEvent.id < before_id)
    return list(db.execute(query).scalars())


@router.get("/audit/verify", response_model=ChainStatus)
def verify_audit_chain(db: Db, _: Admin) -> ChainStatus:
    broken = audit.verify_chain(db)
    return ChainStatus(intact=not broken, broken_event_ids=broken)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Db, _: Admin, status: jobs.JobStatus = jobs.JobStatus.FAILED) -> list[jobs.Job]:
    return list(
        db.execute(
            select(jobs.Job).where(jobs.Job.status == status).order_by(jobs.Job.updated_at.desc())
        ).scalars()
    )


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: uuid.UUID, body: ReasonBody, db: Db, actor: Admin) -> jobs.Job:
    return jobs.retry_failed(db, actor_id=actor.id, job_id=job_id, reason=body.reason)


@router.post("/jobs/{job_id}/resolve", response_model=JobOut)
def resolve_job(job_id: uuid.UUID, body: ReasonBody, db: Db, actor: Admin) -> jobs.Job:
    return jobs.resolve_failed(db, actor_id=actor.id, job_id=job_id, resolution=body.reason)

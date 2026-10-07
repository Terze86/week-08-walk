import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core import jobs
from app.core.errors import ReasonRequired

calls: list[dict] = []


@jobs.job_handler("test.ok")
def _ok(session: Session, payload: dict) -> None:
    calls.append(payload)


@jobs.job_handler("test.fail")
def _fail(session: Session, payload: dict) -> None:
    raise RuntimeError("printer offline")


def _make_due(db: Session, job: jobs.Job) -> None:
    db.execute(update(jobs.Job).where(jobs.Job.id == job.id).values(run_after=jobs.func.now()))
    db.refresh(job)


def test_successful_job(db: Session) -> None:
    job = jobs.enqueue(db, "test.ok", {"label": "EX1"}, requested_by=None)
    assert jobs.run_next(db) is job
    assert job.status == jobs.JobStatus.SUCCEEDED and calls[-1] == {"label": "EX1"}


@pytest.mark.urs("WF-19.03")
def test_failed_job_is_retried_then_surfaced_for_admin(db: Session, staff) -> None:
    job = jobs.enqueue(db, "test.fail", {}, requested_by=None, max_attempts=2)
    jobs.run_next(db)
    assert job.status == jobs.JobStatus.QUEUED and job.attempts == 1
    _make_due(db, job)
    jobs.run_next(db)
    assert job.status == jobs.JobStatus.FAILED and "printer offline" in (job.last_error or "")

    with pytest.raises(ReasonRequired):
        jobs.retry_failed(db, actor_id=staff["admin1"].id, job_id=job.id, reason="")
    jobs.retry_failed(db, actor_id=staff["admin1"].id, job_id=job.id, reason="Printer restarted")
    assert job.status == jobs.JobStatus.QUEUED and job.attempts == 0

    _make_due(db, job)
    jobs.run_next(db)
    _make_due(db, job)
    jobs.run_next(db)
    jobs.resolve_failed(
        db, actor_id=staff["admin1"].id, job_id=job.id, resolution="Labels printed manually"
    )
    assert job.status == jobs.JobStatus.RESOLVED

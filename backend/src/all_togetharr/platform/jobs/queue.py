"""Enqueue and claim jobs from the persistent job table."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from all_togetharr.platform.jobs.models import Job, JobStatus


def enqueue(
    session: Session,
    name: str,
    payload: dict | None = None,
    *,
    run_at: datetime | None = None,
    max_attempts: int = 3,
) -> Job:
    """Add a job to the queue.  The job belongs to the caller's transaction."""
    if run_at is not None and run_at.tzinfo is None:
        raise ValueError("run_at must be timezone-aware")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    if run_at is None:
        run_at = datetime.now(UTC)

    job = Job(
        name=name,
        payload=payload or {},
        run_at=run_at,
        max_attempts=max_attempts,
    )
    session.add(job)
    session.flush()
    return job


def claim_next(session: Session, now: datetime | None = None) -> Job | None:
    """Atomically claim the earliest due pending job.

    Commits the transaction whether or not a row was matched.
    """
    if now is None:
        now = datetime.now(UTC)

    subq = (
        select(Job.id)
        .where(Job.status == JobStatus.PENDING)
        .where(Job.run_at <= now)
        .order_by(Job.run_at, Job.id)
        .limit(1)
    )

    subq = subq.with_for_update(skip_locked=True)

    stmt = (
        update(Job)
        .where(Job.id == subq.scalar_subquery())
        .where(Job.status == JobStatus.PENDING)
        .values(
            status=JobStatus.RUNNING,
            attempts=Job.attempts + 1,
            started_at=now,
        )
        .returning(Job.id)
        .execution_options(synchronize_session=False)
    )

    row = session.execute(stmt).scalar_one_or_none()

    session.commit()

    if row is None:
        return None

    return session.get(Job, row, populate_existing=True)

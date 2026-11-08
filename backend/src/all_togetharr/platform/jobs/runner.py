"""In-process job runner with retries, recovery and recurring schedules."""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from all_togetharr.platform.jobs.models import Job, JobStatus
from all_togetharr.platform.jobs.queue import claim_next, enqueue

logger = logging.getLogger("all_togetharr.jobs")


class _Schedule:
    __slots__ = ("name", "interval", "payload", "max_attempts")

    def __init__(
        self,
        name: str,
        interval: timedelta,
        payload: dict | None,
        max_attempts: int,
    ) -> None:
        self.name = name
        self.interval = interval
        self.payload = payload
        self.max_attempts = max_attempts


class JobRunner:
    def __init__(
        self,
        session_factory: sessionmaker,
        *,
        poll_interval: float = 1.0,
        backoff_base: timedelta = timedelta(seconds=30),
        backoff_max: timedelta = timedelta(hours=1),
        stop_timeout: float = 30.0,
    ) -> None:
        self.session_factory = session_factory
        self.poll_interval = poll_interval
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.stop_timeout = stop_timeout
        self._handlers: dict[str, Callable[[Session, dict], None]] = {}
        self._schedules: dict[str, _Schedule] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- registration --------------------------------------------------------

    def register(self, name: str, handler: Callable[[Session, dict], None]) -> None:
        if name in self._handlers:
            raise ValueError(f"handler already registered: {name}")
        self._handlers[name] = handler

    def every(
        self,
        name: str,
        interval: timedelta,
        *,
        payload: dict | None = None,
        max_attempts: int = 3,
    ) -> None:
        if interval <= timedelta(0):
            raise ValueError("interval must be positive")
        self._schedules[name] = _Schedule(name, interval, payload, max_attempts)

    # -- single execution ----------------------------------------------------

    def run_once(self, now: datetime | None = None) -> bool:
        if now is None:
            now = datetime.now(UTC)

        with self.session_factory() as session:
            # 1. Schedule recurring jobs
            for sched in self._schedules.values():
                has_active = (
                    session.query(Job)
                    .filter(Job.name == sched.name)
                    .filter(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))
                    .count() > 0
                )
                if has_active:
                    continue

                latest_finished = (
                    session.query(func.max(Job.finished_at))
                    .filter(Job.name == sched.name)
                    .scalar()
                )

                if latest_finished is not None:
                    next_run_at = latest_finished + sched.interval
                else:
                    next_run_at = now

                enqueue(
                    session,
                    sched.name,
                    payload=sched.payload,
                    run_at=next_run_at,
                    max_attempts=sched.max_attempts,
                )
                session.commit()

            # 2. Claim and process a job
            job = claim_next(session, now=now)
            if job is None:
                return False

            # 3. No handler
            if job.name not in self._handlers:
                job.status = JobStatus.FAILED
                job.finished_at = now
                job.last_error = f"No handler for job '{job.name}'"
                session.commit()
                logger.error("No handler for job '%s'", job.name)
                return True

            # 4. Call handler
            job_id = job.id
            try:
                self._handlers[job.name](session, job.payload)
                job.status = JobStatus.SUCCEEDED
                job.finished_at = now
                job.last_error = None
                session.commit()
                return True
            except Exception as exc:
                session.rollback()
                job = session.get(Job, job_id, populate_existing=True)
                job.last_error = f"{type(exc).__name__}: {exc}"
                if job.attempts >= job.max_attempts:
                    job.status = JobStatus.FAILED
                    job.finished_at = now
                else:
                    job.status = JobStatus.PENDING
                    exp = min(job.attempts - 1, 30)
                    delay = self.backoff_base * (2 ** exp)
                    if delay > self.backoff_max:
                        delay = self.backoff_max
                    job.run_at = now + delay
                session.commit()
                logger.exception("Job '%s' failed", job.name)
                return True

    # -- recovery ------------------------------------------------------------

    def recover(self, now: datetime | None = None) -> None:
        if now is None:
            now = datetime.now(UTC)

        with self.session_factory() as session:
            running = (
                session.query(Job)
                .filter(Job.status == JobStatus.RUNNING)
                .all()
            )
            count = 0
            for job in running:
                if job.attempts >= job.max_attempts:
                    job.status = JobStatus.FAILED
                    job.finished_at = now
                    job.last_error = "interrupted"
                else:
                    job.status = JobStatus.PENDING
                    job.run_at = now
                    job.started_at = None
                count += 1
            session.commit()
            if count > 0:
                logger.warning("Recovered %d interrupted job(s)", count)

    # -- lifecycle -----------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            ran = False
            try:
                ran = self.run_once()
            except Exception:
                logger.exception("Unexpected error in job loop")
            if not ran:
                self._stop_event.wait(self.poll_interval)

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.stop_timeout)
            if self._thread.is_alive():
                logger.warning("Runner stop timed out after %.1fs", self.stop_timeout)

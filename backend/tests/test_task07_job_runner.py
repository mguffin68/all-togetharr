"""Task 7: in-process job runner with retries, recovery and recurring jobs."""

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from all_togetharr.main import create_app
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.jobs.models import Job, JobStatus
from all_togetharr.platform.jobs.queue import claim_next, enqueue
from all_togetharr.platform.jobs.runner import JobRunner
from all_togetharr.platform.migrations import run_migrations

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
WAIT = 5


@pytest.fixture
def engine(settings):
    db_engine = create_db_engine(settings)
    run_migrations(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture
def runner(session_factory):
    job_runner = JobRunner(session_factory, poll_interval=0.01)
    yield job_runner
    job_runner.stop()


def add_job(session_factory, name="task", run_at=NOW, **kwargs):
    with session_factory() as session:
        job_id = enqueue(session, name, run_at=run_at, **kwargs).id
        session.commit()
    return job_id


def get_job(session_factory, job_id):
    with session_factory() as session:
        return session.get(Job, job_id)


def jobs_named(session_factory, name):
    with session_factory() as session:
        return list(session.scalars(select(Job).where(Job.name == name).order_by(Job.id)))


def failing_handler(session, payload):
    raise RuntimeError("boom")


def noop_handler(session, payload):
    pass


# Running jobs


def test_run_once_returns_false_with_nothing_due(runner):
    assert runner.run_once(now=NOW) is False


def test_run_once_runs_a_due_job_and_marks_it_succeeded(runner, session_factory):
    seen = []
    runner.register("task", lambda session, payload: seen.append(payload))
    job_id = add_job(session_factory, payload={"title_id": 5})

    assert runner.run_once(now=NOW) is True

    job = get_job(session_factory, job_id)
    assert seen == [{"title_id": 5}]
    assert job.status is JobStatus.SUCCEEDED
    assert job.finished_at == NOW
    assert job.last_error is None


def test_handler_work_commits_with_the_job(runner, session_factory):
    runner.register("task", lambda session, payload: enqueue(session, "follow-up", run_at=NOW))
    add_job(session_factory)

    runner.run_once(now=NOW)

    assert len(jobs_named(session_factory, "follow-up")) == 1


def test_handler_work_rolls_back_when_it_fails(runner, session_factory):
    def handler(session, payload):
        enqueue(session, "follow-up", run_at=NOW)
        session.flush()
        raise RuntimeError("boom")

    runner.register("task", handler)
    add_job(session_factory)

    runner.run_once(now=NOW)

    assert jobs_named(session_factory, "follow-up") == []


def test_registering_a_name_twice_is_rejected(runner):
    runner.register("task", noop_handler)

    with pytest.raises(ValueError):
        runner.register("task", noop_handler)


def test_job_with_no_handler_fails_without_retrying(runner, session_factory):
    job_id = add_job(session_factory, name="unknown")

    assert runner.run_once(now=NOW) is True

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.FAILED
    assert job.attempts == 1
    assert job.finished_at == NOW
    assert "unknown" in job.last_error


# Retries


def test_failed_job_is_rescheduled_with_backoff(runner, session_factory):
    runner.register("task", failing_handler)
    job_id = add_job(session_factory)

    assert runner.run_once(now=NOW) is True

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.PENDING
    assert job.attempts == 1
    assert job.run_at == NOW + timedelta(seconds=30)
    assert job.finished_at is None
    assert "RuntimeError: boom" in job.last_error


def test_backoff_doubles_on_each_failure(runner, session_factory):
    runner.register("task", failing_handler)
    job_id = add_job(session_factory)
    second_try = NOW + timedelta(seconds=30)

    runner.run_once(now=NOW)
    runner.run_once(now=second_try)

    assert get_job(session_factory, job_id).run_at == second_try + timedelta(seconds=60)


def test_backoff_is_capped(session_factory):
    runner = JobRunner(session_factory, backoff_max=timedelta(hours=1))
    runner.register("task", failing_handler)
    job_id = add_job(session_factory, max_attempts=50)
    with session_factory() as session:
        session.get(Job, job_id).attempts = 20
        session.commit()

    runner.run_once(now=NOW)

    assert get_job(session_factory, job_id).run_at == NOW + timedelta(hours=1)


def test_job_stays_failed_after_max_attempts(runner, session_factory):
    runner.register("task", failing_handler)
    job_id = add_job(session_factory, max_attempts=2)
    second_try = NOW + timedelta(seconds=30)

    runner.run_once(now=NOW)
    runner.run_once(now=second_try)

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.FAILED
    assert job.attempts == 2
    assert job.finished_at == second_try
    assert "RuntimeError: boom" in job.last_error
    assert runner.run_once(now=NOW + timedelta(days=1)) is False


def test_success_after_a_retry_clears_the_error(runner, session_factory):
    outcomes = iter([RuntimeError("boom"), None])

    def handler(session, payload):
        outcome = next(outcomes)
        if outcome:
            raise outcome

    runner.register("task", handler)
    job_id = add_job(session_factory)

    runner.run_once(now=NOW)
    runner.run_once(now=NOW + timedelta(seconds=30))

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.SUCCEEDED
    assert job.last_error is None


def test_failures_are_logged_with_the_job_name(runner, session_factory, caplog):
    runner.register("task", failing_handler)
    add_job(session_factory)

    runner.run_once(now=NOW)

    assert "task" in caplog.text
    assert "boom" in caplog.text


# Crash recovery


def test_recover_requeues_jobs_left_running(runner, session_factory):
    job_id = add_job(session_factory)
    with session_factory() as session:
        claim_next(session, now=NOW)

    later = NOW + timedelta(minutes=5)
    runner.recover(now=later)

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.PENDING
    assert job.run_at == later
    assert job.started_at is None
    assert job.attempts == 1


def test_recover_fails_jobs_with_no_attempts_left(runner, session_factory):
    job_id = add_job(session_factory, max_attempts=1)
    with session_factory() as session:
        claim_next(session, now=NOW)

    later = NOW + timedelta(minutes=5)
    runner.recover(now=later)

    job = get_job(session_factory, job_id)
    assert job.status is JobStatus.FAILED
    assert job.finished_at == later
    assert "interrupted" in job.last_error


def test_recover_leaves_other_jobs_alone(runner, session_factory):
    job_id = add_job(session_factory)

    runner.recover(now=NOW + timedelta(minutes=5))

    assert get_job(session_factory, job_id).run_at == NOW


# Recurring jobs


def test_recurring_job_runs_then_waits_for_its_interval(runner, session_factory):
    calls = []
    runner.register("rss", lambda session, payload: calls.append(payload))
    runner.every("rss", timedelta(minutes=15), payload={"full": False})

    assert runner.run_once(now=NOW) is True
    assert runner.run_once(now=NOW + timedelta(minutes=14)) is False
    assert runner.run_once(now=NOW + timedelta(minutes=15)) is True

    assert calls == [{"full": False}, {"full": False}]


def test_recurring_job_is_never_queued_twice(runner, session_factory):
    runner.register("rss", noop_handler)
    runner.every("rss", timedelta(minutes=15))

    for _ in range(3):
        runner.run_once(now=NOW)

    with session_factory() as session:
        pending = select(func.count()).select_from(Job).where(Job.status == JobStatus.PENDING)
        assert session.scalar(pending) == 1


def test_recurring_schedule_survives_a_restart(session_factory):
    first = JobRunner(session_factory)
    first.register("rss", noop_handler)
    first.every("rss", timedelta(minutes=15))
    first.run_once(now=NOW)

    second = JobRunner(session_factory)
    second.register("rss", noop_handler)
    second.every("rss", timedelta(minutes=15))

    assert second.run_once(now=NOW + timedelta(minutes=1)) is False
    assert second.run_once(now=NOW + timedelta(minutes=15)) is True


def test_recurring_job_continues_after_a_permanent_failure(runner, session_factory):
    runner.register("rss", failing_handler)
    runner.every("rss", timedelta(minutes=15), max_attempts=1)

    runner.run_once(now=NOW)

    assert runner.run_once(now=NOW + timedelta(minutes=15)) is True
    assert len(jobs_named(session_factory, "rss")) == 2


def test_recurring_interval_must_be_positive(runner):
    with pytest.raises(ValueError):
        runner.every("rss", timedelta(0))


# Background thread


def test_started_runner_picks_up_jobs(runner, session_factory):
    done = threading.Event()
    runner.register("task", lambda session, payload: done.set())
    add_job(session_factory)

    runner.start()

    assert done.wait(WAIT)


def test_stop_waits_for_the_running_job(runner, session_factory):
    started = threading.Event()

    def handler(session, payload):
        started.set()
        time.sleep(0.2)

    runner.register("task", handler)
    job_id = add_job(session_factory)
    runner.start()
    assert started.wait(WAIT)

    runner.stop()

    assert get_job(session_factory, job_id).status is JobStatus.SUCCEEDED
    assert runner.is_running is False


def test_start_and_stop_are_safe_to_repeat(runner):
    runner.start()
    thread_count = threading.active_count()

    runner.start()
    assert threading.active_count() == thread_count

    runner.stop()
    runner.stop()
    assert runner.is_running is False


def test_runner_can_restart_after_stopping(runner, session_factory):
    done = threading.Event()
    runner.register("task", lambda session, payload: done.set())
    runner.start()
    runner.stop()
    add_job(session_factory)

    runner.start()

    assert done.wait(WAIT)


def test_loop_survives_an_unexpected_error(runner, monkeypatch):
    survived = threading.Event()
    calls = []

    def flaky_run_once(now=None):
        calls.append(now)
        if len(calls) == 1:
            raise RuntimeError("database went away")
        survived.set()
        return False

    monkeypatch.setattr(runner, "run_once", flaky_run_once)

    runner.start()

    assert survived.wait(WAIT)


# App integration


def test_runner_starts_and_stops_with_the_app(settings):
    app = create_app(settings)
    runner = app.state.job_runner
    assert runner.is_running is False

    with TestClient(app):
        assert runner.is_running is True

    assert runner.is_running is False


def test_app_runs_queued_jobs(settings):
    app = create_app(settings)
    done = threading.Event()
    app.state.job_runner.poll_interval = 0.01
    app.state.job_runner.register("task", lambda session, payload: done.set())

    with TestClient(app):
        with app.state.session_factory() as session:
            enqueue(session, "task")
            session.commit()

        assert done.wait(WAIT)


def test_app_startup_recovers_interrupted_jobs(settings, engine, session_factory):
    job_id = add_job(session_factory)
    with session_factory() as session:
        claim_next(session, now=NOW)

    app = create_app(settings)
    done = threading.Event()
    app.state.job_runner.poll_interval = 0.01
    app.state.job_runner.register("task", lambda session, payload: done.set())

    with TestClient(app):
        assert done.wait(WAIT)

    assert get_job(session_factory, job_id).attempts == 2

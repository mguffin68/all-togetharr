"""Task 6: persistent job table with enqueue and claim."""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.jobs.models import Job, JobStatus
from all_togetharr.platform.jobs.queue import claim_next, enqueue
from all_togetharr.platform.migrations import run_migrations

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


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
def session(session_factory):
    with session_factory() as db_session:
        yield db_session


def test_models_module_registers_jobs_on_its_own():
    code = "import all_togetharr.models as m; print('jobs' in m.Base.metadata.tables)"

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.stdout.strip() == "True", result.stderr


def add_job(session, name="task", run_at=NOW, **kwargs):
    job = enqueue(session, name, run_at=run_at, **kwargs)
    session.commit()
    return job


def test_enqueue_sets_defaults(session):
    before = datetime.now(UTC)

    job = enqueue(session, "refresh")
    session.commit()

    assert job.id is not None
    assert job.name == "refresh"
    assert job.status is JobStatus.PENDING
    assert job.payload == {}
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.last_error is None
    assert job.started_at is None
    assert job.finished_at is None
    assert before <= job.run_at <= datetime.now(UTC)
    assert job.created_at.utcoffset() == timedelta(0)


def test_payload_survives_a_reload(session):
    job = add_job(session, payload={"title_id": 5, "tags": ["a", "b"]})

    session.expire_all()

    assert job.payload == {"title_id": 5, "tags": ["a", "b"]}


def test_enqueue_joins_the_callers_transaction(session):
    enqueue(session, "refresh")

    session.rollback()

    assert session.scalar(select(func.count()).select_from(Job)) == 0


def test_run_at_is_stored_as_utc(session):
    run_at = datetime(2026, 1, 1, 7, 0, tzinfo=ZoneInfo("America/New_York"))
    job = add_job(session, run_at=run_at)

    session.expire_all()

    assert job.run_at == run_at
    assert job.run_at.utcoffset() == timedelta(0)


def test_naive_run_at_is_rejected(session):
    with pytest.raises(ValueError):
        enqueue(session, "refresh", run_at=datetime(2026, 1, 1, 12, 0))


def test_max_attempts_below_one_is_rejected(session):
    with pytest.raises(ValueError):
        enqueue(session, "refresh", max_attempts=0)


def test_claim_marks_the_job_running(session):
    job = add_job(session, name="refresh")

    claimed = claim_next(session, now=NOW)

    assert claimed.id == job.id
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempts == 1
    assert claimed.started_at == NOW


def test_claim_is_committed(session, session_factory):
    job = add_job(session)

    claim_next(session, now=NOW)

    with session_factory() as other:
        assert other.get(Job, job.id).status is JobStatus.RUNNING


def test_claim_returns_none_when_nothing_is_pending(session):
    assert claim_next(session, now=NOW) is None


def test_claim_skips_jobs_scheduled_for_later(session):
    add_job(session, run_at=NOW + timedelta(seconds=1))

    assert claim_next(session, now=NOW) is None


def test_claim_takes_the_earliest_job_first(session):
    later = add_job(session, run_at=NOW - timedelta(minutes=1))
    earliest = add_job(session, run_at=NOW - timedelta(minutes=2))
    same_time = add_job(session, run_at=NOW - timedelta(minutes=1))

    claimed = [claim_next(session, now=NOW).id for _ in range(3)]

    assert claimed == [earliest.id, later.id, same_time.id]


def test_a_job_cannot_be_claimed_twice(session):
    add_job(session)

    assert claim_next(session, now=NOW) is not None
    assert claim_next(session, now=NOW) is None


def test_concurrent_workers_never_share_a_job(session, session_factory):
    expected = {add_job(session).id for _ in range(20)}

    def drain(_worker):
        claimed = []
        with session_factory() as worker_session:
            while (job := claim_next(worker_session, now=NOW)) is not None:
                claimed.append(job.id)
        return claimed

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(drain, range(4)))

    claimed = [job_id for result in results for job_id in result]
    assert len(claimed) == len(expected)
    assert set(claimed) == expected


def test_database_rejects_an_unknown_status(session):
    job = add_job(session)

    with pytest.raises(IntegrityError):
        session.execute(
            text("update jobs set status = 'bogus' where id = :id"), {"id": job.id}
        )


def test_claim_query_has_an_index(engine):
    indexes = inspect(engine).get_indexes("jobs")

    assert ["status", "run_at"] in [index["column_names"] for index in indexes]

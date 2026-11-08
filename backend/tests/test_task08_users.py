"""Task 8: users, roles and Argon2 password hashing."""

import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest
from argon2 import PasswordHasher
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from all_togetharr.platform.auth.models import AuthSource, Role, User
from all_togetharr.platform.auth.passwords import hash_password, needs_rehash, verify_password
from all_togetharr.platform.auth.users import UserExistsError, create_user
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.migrations import run_migrations

PASSWORD = "correct horse battery"
INSERT_USER = text(
    "insert into users (name, name_key, role, auth_source, password_hash, created_at) "
    "values (:name, :key, :role, :source, :hash, :created)"
)


@pytest.fixture
def engine(settings):
    db_engine = create_db_engine(settings)
    run_migrations(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine):
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


def raw_insert(session, **overrides):
    values = {
        "name": "Mike",
        "key": "mike",
        "role": "admin",
        "source": "local",
        "hash": "hash",
        "created": "2026-01-01 00:00:00",
    }
    session.execute(INSERT_USER, values | overrides)


def test_models_module_registers_users_on_its_own():
    code = "import all_togetharr.models as m; print('users' in m.Base.metadata.tables)"

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.stdout.strip() == "True", result.stderr


# Passwords


def test_hash_uses_argon2id_and_hides_the_password():
    hashed = hash_password(PASSWORD)

    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed


def test_same_password_hashes_differently():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_accepts_the_right_password():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_rejects_the_wrong_password():
    assert verify_password("wrong password", hash_password(PASSWORD)) is False


def test_verify_returns_false_for_a_corrupt_hash():
    assert verify_password(PASSWORD, "not-a-real-hash") is False


def test_fresh_hash_does_not_need_rehashing():
    assert needs_rehash(hash_password(PASSWORD)) is False


def test_weak_hash_needs_rehashing():
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)

    assert needs_rehash(weak) is True


# Creating users


def test_create_local_user(session):
    user = create_user(session, "Mike", Role.ADMIN, password=PASSWORD)
    session.commit()
    session.expire_all()

    assert user.id is not None
    assert user.name == "Mike"
    assert user.role is Role.ADMIN
    assert user.auth_source is AuthSource.LOCAL
    assert user.created_at.utcoffset() == timedelta(0)
    assert user.created_at <= datetime.now(UTC)


def test_password_is_stored_only_as_a_hash(session):
    user = create_user(session, "Mike", Role.ADMIN, password=PASSWORD)

    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash) is True


def test_create_user_joins_the_callers_transaction(session):
    create_user(session, "Mike", Role.ADMIN, password=PASSWORD)

    session.rollback()

    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_all_four_roles_exist():
    assert {role.value for role in Role} == {"admin", "manager", "requester", "viewer"}


def test_all_three_auth_sources_exist():
    assert {source.value for source in AuthSource} == {"local", "jellyfin", "oidc"}


def test_name_is_trimmed(session):
    user = create_user(session, "  Mike  ", Role.VIEWER, password=PASSWORD)

    assert user.name == "Mike"


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_rejected(session, name):
    with pytest.raises(ValueError):
        create_user(session, name, Role.VIEWER, password=PASSWORD)


def test_name_over_100_characters_is_rejected(session):
    with pytest.raises(ValueError):
        create_user(session, "x" * 101, Role.VIEWER, password=PASSWORD)


def test_duplicate_name_is_rejected_regardless_of_case(session):
    create_user(session, "Mike", Role.ADMIN, password=PASSWORD)

    with pytest.raises(UserExistsError):
        create_user(session, "MIKE", Role.VIEWER, password=PASSWORD)


def test_user_exists_error_leaves_the_session_usable(session):
    create_user(session, "Mike", Role.ADMIN, password=PASSWORD)

    with pytest.raises(UserExistsError):
        create_user(session, "mike", Role.VIEWER, password=PASSWORD)

    assert create_user(session, "Other", Role.VIEWER, password=PASSWORD).id is not None


@pytest.mark.parametrize("password", ["short", "x" * 7, "x" * 1025])
def test_password_length_limits(session, password):
    with pytest.raises(ValueError):
        create_user(session, "Mike", Role.VIEWER, password=password)


def test_local_user_needs_a_password(session):
    with pytest.raises(ValueError):
        create_user(session, "Mike", Role.VIEWER)


def test_external_user_has_no_password_hash(session):
    user = create_user(session, "Mike", Role.VIEWER, auth_source=AuthSource.JELLYFIN)

    assert user.auth_source is AuthSource.JELLYFIN
    assert user.password_hash is None


def test_external_user_cannot_set_a_password(session):
    with pytest.raises(ValueError):
        create_user(
            session, "Mike", Role.VIEWER, password=PASSWORD, auth_source=AuthSource.JELLYFIN
        )


# Database rules


def test_check_constraints_use_the_naming_convention(engine):
    names = {check["name"] for check in inspect(engine).get_check_constraints("users")}

    assert names == {"ck_users_local_has_password", "ck_users_role", "ck_users_auth_source"}


def test_database_rejects_a_local_user_with_no_hash(session):
    with pytest.raises(IntegrityError):
        raw_insert(session, hash=None)


def test_database_rejects_an_unknown_role(session):
    with pytest.raises(IntegrityError):
        raw_insert(session, role="owner")


def test_database_rejects_an_unknown_auth_source(session):
    with pytest.raises(IntegrityError):
        raw_insert(session, source="ldap")


def test_database_rejects_a_duplicate_name_key(session):
    raw_insert(session)

    with pytest.raises(IntegrityError):
        raw_insert(session, name="MIKE")

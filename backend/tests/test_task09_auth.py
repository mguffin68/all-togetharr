"""Task 9: first-run setup, login, sessions and role checks."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from argon2 import PasswordHasher
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update

from all_togetharr.main import create_app
from all_togetharr.platform.auth import users as users_module
from all_togetharr.platform.auth.deps import get_current_user, require_role
from all_togetharr.platform.auth.models import AuthSession, AuthSource, Role, User
from all_togetharr.platform.auth.passwords import needs_rehash
from all_togetharr.platform.auth.sessions import SESSION_COOKIE, SESSION_LIFETIME
from all_togetharr.platform.auth.users import authenticate, create_user
from all_togetharr.platform.settings import Settings

PASSWORD = "correct horse battery"
SETUP = "/api/v1/auth/setup"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"

CurrentUser = Annotated[User, Depends(get_current_user)]
ManagerUser = Annotated[User, Depends(require_role(Role.MANAGER))]


@pytest.fixture
def role_client(settings):
    app = create_app(settings)

    @app.get("/probe/any")
    def any_user(user: CurrentUser):
        return {"name": user.name}

    @app.get("/probe/manager")
    def manager_only(user: ManagerUser):
        return {"name": user.name}

    with TestClient(app) as client:
        yield client


def session_factory(client):
    return client.app.state.session_factory


def add_user(client, name="Mike", role=Role.ADMIN, password=PASSWORD, **kwargs):
    with session_factory(client)() as session:
        user_id = create_user(session, name, role, password=password, **kwargs).id
        session.commit()
    return user_id


def login(client, name="Mike", password=PASSWORD):
    return client.post(LOGIN, json={"name": name, "password": password})


def session_count(client):
    with session_factory(client)() as session:
        return session.scalar(select(func.count()).select_from(AuthSession))


# First-run setup


def test_setup_is_required_with_no_users(client):
    assert client.get(SETUP).json() == {"required": True}


def test_setup_is_not_required_once_a_user_exists(client):
    add_user(client)

    assert client.get(SETUP).json() == {"required": False}


def test_setup_creates_the_first_admin_and_logs_them_in(client):
    response = client.post(SETUP, json={"name": "Mike", "password": PASSWORD})

    assert response.status_code == 201
    assert response.json()["name"] == "Mike"
    assert response.json()["role"] == "admin"
    assert client.get(ME).json()["name"] == "Mike"


def test_second_setup_returns_409(client):
    client.post(SETUP, json={"name": "Mike", "password": PASSWORD})

    response = client.post(SETUP, json={"name": "Other", "password": PASSWORD})

    assert response.status_code == 409


def test_setup_is_closed_when_any_user_exists(client):
    add_user(client, role=Role.VIEWER)

    response = client.post(SETUP, json={"name": "Other", "password": PASSWORD})

    assert response.status_code == 409


def test_setup_rejects_a_weak_password_and_creates_nothing(client):
    response = client.post(SETUP, json={"name": "Mike", "password": "short"})

    assert response.status_code == 422
    assert client.get(SETUP).json() == {"required": True}


# Login


def test_login_returns_the_user(client):
    add_user(client, role=Role.MANAGER)

    response = login(client)

    assert response.status_code == 200
    assert response.json()["name"] == "Mike"
    assert response.json()["role"] == "manager"
    assert response.json()["auth_source"] == "local"


def test_login_ignores_name_case_and_spaces(client):
    add_user(client)

    assert login(client, name="  MIKE ").status_code == 200


def test_login_cookie_flags(client):
    add_user(client)

    cookie = login(client).headers["set-cookie"].lower()

    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert f"max-age={int(SESSION_LIFETIME.total_seconds())}" in cookie
    assert "secure" not in cookie


def test_secure_cookie_setting(settings):
    secure_settings = settings.model_copy(update={"cookie_secure": True})

    with TestClient(create_app(secure_settings)) as client:
        add_user(client)
        cookie = login(client).headers["set-cookie"].lower()

    assert "secure" in cookie


def test_cookie_secure_is_read_from_the_environment(monkeypatch):
    assert Settings().cookie_secure is False

    monkeypatch.setenv("COOKIE_SECURE", "true")

    assert Settings().cookie_secure is True


def test_wrong_password_and_unknown_user_look_the_same(client):
    add_user(client)

    wrong_password = login(client, password="wrong password")
    unknown_user = login(client, name="Nobody")

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert "set-cookie" not in wrong_password.headers


def test_external_users_cannot_use_password_login(client):
    add_user(client, password=None, auth_source=AuthSource.JELLYFIN)

    assert login(client, password="anything at all").status_code == 401


def test_login_needs_a_name_and_password(client):
    assert client.post(LOGIN, json={"name": "Mike"}).status_code == 422


def test_login_rejects_an_oversized_password_without_hashing(client, monkeypatch):
    def fail(password, password_hash):
        raise AssertionError("oversized password reached the hasher")

    monkeypatch.setattr(users_module, "verify_password", fail)

    assert login(client, password="x" * 1025).status_code == 422


def test_invalid_unicode_in_a_password_is_rejected(client):
    body = b'{"name": "Mike", "password": "\\ud800 not valid unicode"}'

    response = client.post(LOGIN, content=body, headers={"content-type": "application/json"})

    assert response.status_code == 422


def test_authenticate_checks_a_hash_even_for_unknown_users(client, monkeypatch):
    calls = []
    real_verify = users_module.verify_password

    def spy(password, password_hash):
        calls.append(password_hash)
        return real_verify(password, password_hash)

    monkeypatch.setattr(users_module, "verify_password", spy)

    with session_factory(client)() as session:
        assert authenticate(session, "Nobody", PASSWORD) is None

    assert len(calls) == 1


def test_login_upgrades_an_outdated_hash(client):
    user_id = add_user(client)
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)
    with session_factory(client)() as session:
        session.get(User, user_id).password_hash = weak
        session.commit()

    assert login(client).status_code == 200

    with session_factory(client)() as session:
        stored = session.get(User, user_id).password_hash
    assert stored != weak
    assert needs_rehash(stored) is False


def test_responses_never_include_the_password_hash(client):
    add_user(client)

    assert "password_hash" not in login(client).text
    assert "password_hash" not in client.get(ME).text


# Sessions


def test_me_needs_a_session(client):
    assert client.get(ME).status_code == 401


def test_me_returns_the_logged_in_user(client):
    add_user(client)
    login(client)

    assert client.get(ME).json()["name"] == "Mike"


def test_garbage_cookie_is_rejected(client):
    client.cookies.set(SESSION_COOKIE, "garbage")

    assert client.get(ME).status_code == 401


def test_only_a_hash_of_the_token_is_stored(client):
    add_user(client)
    login(client)
    token = client.cookies[SESSION_COOKIE]

    with session_factory(client)() as session:
        stored = session.scalars(select(AuthSession.token_hash)).one()

    assert stored != token
    assert len(stored) == 64


def test_session_expires_after_its_lifetime(client):
    add_user(client)
    before = datetime.now(UTC)
    login(client)

    with session_factory(client)() as session:
        expires_at = session.scalars(select(AuthSession.expires_at)).one()

    assert expires_at >= before + SESSION_LIFETIME


def test_expired_session_is_rejected(client):
    add_user(client)
    login(client)
    with session_factory(client)() as session:
        session.execute(update(AuthSession).values(expires_at=datetime.now(UTC) - timedelta(1)))
        session.commit()

    assert client.get(ME).status_code == 401


def test_deleting_a_user_ends_their_sessions(client):
    user_id = add_user(client)
    login(client)

    with session_factory(client)() as session:
        session.execute(delete(User).where(User.id == user_id))
        session.commit()

    assert session_count(client) == 0
    assert client.get(ME).status_code == 401


# Logout


def test_logout_ends_the_session_and_clears_the_cookie(client):
    add_user(client)
    login(client)

    response = client.post(LOGOUT)

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert session_count(client) == 0
    assert client.get(ME).status_code == 401


def test_old_cookie_stops_working_after_logout(client):
    add_user(client)
    login(client)
    token = client.cookies[SESSION_COOKIE]

    client.post(LOGOUT)
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, token)

    assert client.get(ME).status_code == 401


def test_logout_without_a_session_is_harmless(client):
    assert client.post(LOGOUT).status_code == 204


def test_logout_only_ends_the_current_session(settings):
    with TestClient(create_app(settings)) as first:
        add_user(first)
        login(first)
        token = first.cookies[SESSION_COOKIE]
        first.cookies.clear()
        login(first)

        first.post(LOGOUT)
        first.cookies.clear()
        first.cookies.set(SESSION_COOKIE, token)

        assert first.get(ME).status_code == 200


# Role checks


def test_protected_route_returns_401_with_no_session(role_client):
    assert role_client.get("/probe/any").status_code == 401
    assert role_client.get("/probe/manager").status_code == 401


def test_any_logged_in_user_passes_get_current_user(role_client):
    add_user(role_client, role=Role.VIEWER)
    login(role_client)

    assert role_client.get("/probe/any").json() == {"name": "Mike"}


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (Role.VIEWER, 403),
        (Role.REQUESTER, 403),
        (Role.MANAGER, 200),
        (Role.ADMIN, 200),
    ],
)
def test_require_role_allows_that_role_and_above(role_client, role, status):
    add_user(role_client, role=role)
    login(role_client)

    assert role_client.get("/probe/manager").status_code == status


def test_role_changes_apply_to_existing_sessions(role_client):
    user_id = add_user(role_client, role=Role.ADMIN)
    login(role_client)
    with session_factory(role_client)() as session:
        session.get(User, user_id).role = Role.VIEWER
        session.commit()

    assert role_client.get("/probe/manager").status_code == 403


# Public routes


def test_health_and_docs_stay_public_after_setup(client):
    add_user(client)

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/docs").status_code == 200


@pytest.mark.parametrize(
    ("path", "method", "status"),
    [(SETUP, "post", "201"), (LOGIN, "post", "200"), (ME, "get", "200")],
)
def test_user_routes_document_their_response(client, path, method, status):
    spec = client.get("/api/openapi.json").json()

    content = spec["paths"][path][method]["responses"][status]["content"]

    assert content["application/json"]["schema"] == {"$ref": "#/components/schemas/UserResponse"}


def test_auth_routes_are_in_the_openapi_spec(client):
    paths = client.get("/api/openapi.json").json()["paths"]

    assert {SETUP, LOGIN, LOGOUT, ME} <= set(paths)

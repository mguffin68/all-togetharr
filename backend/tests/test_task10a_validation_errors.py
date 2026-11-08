"""Task 10a: validation errors never echo input and never crash."""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator

from all_togetharr.main import create_app
from all_togetharr.platform.auth import routes as auth_routes
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.auth.users import create_user

LOGIN = "/api/v1/auth/login"
SECRET = "do-not-echo-this-value"
JSON_HEADERS = {"content-type": "application/json"}


class Picky(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def reject(cls, value):
        raise ValueError("bad value")


@pytest.fixture
def picky_client(settings):
    app = create_app(settings)

    @app.post("/probe")
    def probe(body: Picky):
        return {}

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_oversized_password_is_not_echoed(client):
    response = client.post(LOGIN, json={"name": "Mike", "password": SECRET * 100})

    assert response.status_code == 422
    assert SECRET not in response.text


def test_missing_field_does_not_echo_the_rest_of_the_body(client):
    response = client.post(LOGIN, json={"password": SECRET})

    assert response.status_code == 422
    assert SECRET not in response.text


def test_malformed_json_is_not_echoed(client):
    body = f'{{"name": "Mike", "password": "{SECRET}"'

    response = client.post(LOGIN, content=body, headers=JSON_HEADERS)

    assert response.status_code == 422
    assert SECRET not in response.text


def test_wrong_type_in_settings_is_not_echoed(client):
    password = "correct horse battery"
    with client.app.state.session_factory() as session:
        create_user(session, "Mike", Role.ADMIN, password=password)
        session.commit()
    client.post(LOGIN, json={"name": "Mike", "password": password})

    response = client.put("/api/v1/settings/tmdb.api_key", json={"value": [SECRET]})

    assert response.status_code == 422
    assert SECRET not in response.text


def test_errors_contain_only_type_loc_and_msg(client):
    response = client.post(LOGIN, json={"password": SECRET})

    (error,) = response.json()["detail"]
    assert set(error) == {"type", "loc", "msg"}
    assert error["loc"] == ["body", "name"]


@pytest.mark.parametrize("field", ["name", "password"])
def test_invalid_unicode_returns_structured_errors(client, field):
    values = {"name": '"Mike"', "password": '"long enough password"'}
    values[field] = '"\\ud800 text"'
    body = f'{{"name": {values["name"]}, "password": {values["password"]}}}'

    response = client.post(LOGIN, content=body, headers=JSON_HEADERS)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_validator_errors_are_reported_without_crashing(picky_client):
    response = picky_client.post("/probe", json={"value": SECRET})

    assert response.status_code == 422
    assert "bad value" in response.json()["detail"][0]["msg"]
    assert SECRET not in response.text


def test_routes_rely_on_pydantic_for_unicode_checks():
    assert not hasattr(auth_routes, "_accept_utf8")

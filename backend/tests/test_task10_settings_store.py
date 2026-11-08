"""Task 10: encrypted settings store and admin settings API."""

import stat
import subprocess
import sys
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from all_togetharr.main import create_app
from all_togetharr.platform import secrets as secrets_module
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.auth.users import create_user
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.migrations import run_migrations
from all_togetharr.platform.secrets import (
    KEY_FILENAME,
    SecretBox,
    SecretDecryptError,
    load_or_create_key,
)
from all_togetharr.platform.settings_routes import router as settings_router
from all_togetharr.platform.settings_store import Setting, SettingsStore, UnknownSettingError

PASSWORD = "correct horse battery"
SECRET_KEY = "tmdb.api_key"
PLAIN_KEY = "tmdb.language"
SECRET_VALUE = "super-secret-api-key"
SETTINGS_URL = "/api/v1/settings"


@pytest.fixture
def box(tmp_path):
    return SecretBox(load_or_create_key(tmp_path / "keys"))


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


@pytest.fixture
def store(session, box):
    return SettingsStore(session, box)


def raw_value(session, key):
    return session.execute(
        text("select value from settings where key = :key"), {"key": key}
    ).scalar_one()


def login_as(client, role=Role.ADMIN, name="Mike"):
    with client.app.state.session_factory() as session:
        create_user(session, name, role, password=PASSWORD)
        session.commit()
    client.post("/api/v1/auth/login", json={"name": name, "password": PASSWORD})


def test_models_module_registers_settings_on_its_own():
    code = "import all_togetharr.models as m; print('settings' in m.Base.metadata.tables)"

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.stdout.strip() == "True", result.stderr


# Key file


def test_key_file_is_created_with_owner_only_permissions(tmp_path):
    load_or_create_key(tmp_path)

    mode = (tmp_path / KEY_FILENAME).stat().st_mode

    assert stat.S_IMODE(mode) == 0o600


def test_key_is_created_in_a_missing_config_dir(tmp_path):
    load_or_create_key(tmp_path / "new" / "config")

    assert (tmp_path / "new" / "config" / KEY_FILENAME).exists()


def test_key_is_reused_on_later_runs(tmp_path):
    assert load_or_create_key(tmp_path) == load_or_create_key(tmp_path)


def test_loose_key_permissions_are_tightened(tmp_path):
    load_or_create_key(tmp_path)
    (tmp_path / KEY_FILENAME).chmod(0o644)

    load_or_create_key(tmp_path)

    assert stat.S_IMODE((tmp_path / KEY_FILENAME).stat().st_mode) == 0o600


def test_corrupt_key_is_an_error_and_is_not_replaced(tmp_path):
    key_file = tmp_path / KEY_FILENAME
    key_file.write_text("not a valid key")

    with pytest.raises(ValueError):
        load_or_create_key(tmp_path)

    assert key_file.read_text() == "not a valid key"


def test_losing_the_key_creation_race_uses_the_winners_key(tmp_path, monkeypatch):
    winner = load_or_create_key(tmp_path)
    real_exists = secrets_module.Path.exists
    monkeypatch.setattr(secrets_module.Path, "exists", lambda self: False)

    key = load_or_create_key(tmp_path)

    monkeypatch.setattr(secrets_module.Path, "exists", real_exists)
    assert key == winner


def test_corrupt_key_error_names_the_file(tmp_path):
    (tmp_path / KEY_FILENAME).write_text("not a valid key")

    with pytest.raises(ValueError, match=KEY_FILENAME):
        load_or_create_key(tmp_path)


# Encryption


def test_encrypt_round_trip(box):
    assert box.decrypt(box.encrypt(SECRET_VALUE)) == SECRET_VALUE


def test_box_encrypts_the_exact_text_it_is_given(tmp_path):
    key = load_or_create_key(tmp_path)

    token = SecretBox(key).encrypt(SECRET_VALUE)

    assert Fernet(key).decrypt(token.encode()).decode() == SECRET_VALUE


def test_ciphertext_hides_the_value(box):
    assert SECRET_VALUE not in box.encrypt(SECRET_VALUE)


def test_same_value_encrypts_differently(box):
    assert box.encrypt(SECRET_VALUE) != box.encrypt(SECRET_VALUE)


def test_decrypting_with_the_wrong_key_raises(box, tmp_path):
    other = SecretBox(load_or_create_key(tmp_path / "other"))

    with pytest.raises(SecretDecryptError):
        other.decrypt(box.encrypt(SECRET_VALUE))


def test_decrypting_garbage_raises(box):
    with pytest.raises(SecretDecryptError):
        box.decrypt("not ciphertext")


# Store


def test_unset_setting_returns_its_default(store):
    assert store.get(PLAIN_KEY) == "en-US"
    assert store.get(SECRET_KEY) is None
    assert store.is_set(PLAIN_KEY) is False


def test_set_and_get_a_plain_setting(store):
    store.set(PLAIN_KEY, "de-DE")

    assert store.get(PLAIN_KEY) == "de-DE"
    assert store.is_set(PLAIN_KEY) is True


def test_plain_setting_is_readable_in_the_database(store, session):
    store.set(PLAIN_KEY, "de-DE")

    assert "de-DE" in raw_value(session, PLAIN_KEY)


def test_secret_setting_round_trips(store):
    store.set(SECRET_KEY, SECRET_VALUE)

    assert store.get(SECRET_KEY) == SECRET_VALUE


def test_secret_setting_is_encrypted_in_the_database(store, session):
    store.set(SECRET_KEY, SECRET_VALUE)

    assert SECRET_VALUE not in raw_value(session, SECRET_KEY)


def test_setting_twice_updates_one_row(store, session):
    store.set(PLAIN_KEY, "de-DE")
    store.set(PLAIN_KEY, "fr-FR")

    assert store.get(PLAIN_KEY) == "fr-FR"
    assert session.scalar(select(func.count()).select_from(Setting)) == 1


def test_updated_at_is_utc(store, session):
    store.set(PLAIN_KEY, "de-DE")
    session.commit()
    session.expire_all()

    assert session.get(Setting, PLAIN_KEY).updated_at.utcoffset() == timedelta(0)


def test_store_joins_the_callers_transaction(store, session):
    store.set(PLAIN_KEY, "de-DE")

    session.rollback()

    assert store.is_set(PLAIN_KEY) is False


def test_delete_returns_a_setting_to_its_default(store):
    store.set(PLAIN_KEY, "de-DE")

    store.delete(PLAIN_KEY)

    assert store.get(PLAIN_KEY) == "en-US"
    assert store.is_set(PLAIN_KEY) is False


def test_deleting_an_unset_setting_is_harmless(store):
    store.delete(PLAIN_KEY)

    assert store.is_set(PLAIN_KEY) is False


@pytest.mark.parametrize("method", ["get", "is_set", "delete"])
def test_unknown_key_raises(store, method):
    with pytest.raises(UnknownSettingError):
        getattr(store, method)("no.such.key")


def test_setting_an_unknown_key_raises(store):
    with pytest.raises(UnknownSettingError):
        store.set("no.such.key", "value")


def test_wrong_value_type_is_rejected(store):
    with pytest.raises(ValueError):
        store.set(PLAIN_KEY, 5)


def test_wrong_key_makes_get_raise_rather_than_return_garbage(store, session, tmp_path):
    store.set(SECRET_KEY, SECRET_VALUE)
    other = SecretBox(load_or_create_key(tmp_path / "other"))

    with pytest.raises(SecretDecryptError):
        SettingsStore(session, other).get(SECRET_KEY)


# App startup


def test_startup_creates_the_key_and_box(settings):
    app = create_app(settings)

    with TestClient(app):
        assert isinstance(app.state.secret_box, SecretBox)

    assert (settings.config_dir / KEY_FILENAME).exists()


def test_create_app_alone_does_not_create_the_key(settings):
    create_app(settings)

    assert not (settings.config_dir / KEY_FILENAME).exists()


def test_secrets_survive_a_restart(settings):
    first = create_app(settings)
    with TestClient(first) as client:
        with client.app.state.session_factory() as session:
            SettingsStore(session, first.state.secret_box).set(SECRET_KEY, SECRET_VALUE)
            session.commit()

    second = create_app(settings)
    with TestClient(second) as client:
        with client.app.state.session_factory() as session:
            assert SettingsStore(session, second.state.secret_box).get(SECRET_KEY) == SECRET_VALUE


def test_corrupt_key_stops_startup(settings):
    settings.config_dir.mkdir(parents=True)
    (settings.config_dir / KEY_FILENAME).write_text("not a valid key")

    with pytest.raises(ValueError):
        with TestClient(create_app(settings)):
            pass


# API


def test_list_shows_every_setting(client):
    login_as(client)

    items = {item["key"]: item for item in client.get(SETTINGS_URL).json()}

    assert items[PLAIN_KEY] == {
        "key": PLAIN_KEY,
        "value": "en-US",
        "secret": False,
        "is_set": False,
    }
    assert items[SECRET_KEY] == {
        "key": SECRET_KEY,
        "value": None,
        "secret": True,
        "is_set": False,
    }


def test_get_one_setting(client):
    login_as(client)

    response = client.get(f"{SETTINGS_URL}/{PLAIN_KEY}")

    assert response.status_code == 200
    assert response.json()["value"] == "en-US"


def test_put_updates_a_plain_setting(client):
    login_as(client)

    response = client.put(f"{SETTINGS_URL}/{PLAIN_KEY}", json={"value": "de-DE"})

    assert response.status_code == 200
    assert response.json()["value"] == "de-DE"
    assert response.json()["is_set"] is True
    assert client.get(f"{SETTINGS_URL}/{PLAIN_KEY}").json()["value"] == "de-DE"


def test_secret_values_are_never_returned(client):
    login_as(client)

    put = client.put(f"{SETTINGS_URL}/{SECRET_KEY}", json={"value": SECRET_VALUE})
    one = client.get(f"{SETTINGS_URL}/{SECRET_KEY}")
    everything = client.get(SETTINGS_URL)

    assert one.json() == {"key": SECRET_KEY, "value": None, "secret": True, "is_set": True}
    for response in (put, one, everything):
        assert response.status_code == 200
        assert SECRET_VALUE not in response.text


def test_secret_values_are_not_logged(client, caplog):
    login_as(client)

    client.put(f"{SETTINGS_URL}/{SECRET_KEY}", json={"value": SECRET_VALUE})

    assert SECRET_VALUE not in caplog.text


def test_put_is_stored_encrypted(client):
    login_as(client)

    client.put(f"{SETTINGS_URL}/{SECRET_KEY}", json={"value": SECRET_VALUE})

    with client.app.state.session_factory() as session:
        assert SECRET_VALUE not in raw_value(session, SECRET_KEY)
        store = SettingsStore(session, client.app.state.secret_box)
        assert store.get(SECRET_KEY) == SECRET_VALUE


def test_delete_resets_a_setting(client):
    login_as(client)
    client.put(f"{SETTINGS_URL}/{PLAIN_KEY}", json={"value": "de-DE"})

    response = client.delete(f"{SETTINGS_URL}/{PLAIN_KEY}")

    assert response.status_code == 204
    assert client.get(f"{SETTINGS_URL}/{PLAIN_KEY}").json()["value"] == "en-US"


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("put", {"value": "x"}), ("delete", None)],
)
def test_unknown_key_returns_404(client, method, body):
    login_as(client)
    kwargs = {} if body is None else {"json": body}

    response = getattr(client, method)(f"{SETTINGS_URL}/no.such.key", **kwargs)

    assert response.status_code == 404


@pytest.mark.parametrize("value", [5, None])
def test_put_rejects_the_wrong_type(client, value):
    login_as(client)

    response = client.put(f"{SETTINGS_URL}/{PLAIN_KEY}", json={"value": value})

    assert response.status_code == 422


def test_admin_check_lives_on_the_router_itself():
    assert settings_router.dependencies != []


REQUESTS = [
    ("get", SETTINGS_URL, None),
    ("get", f"{SETTINGS_URL}/{PLAIN_KEY}", None),
    ("put", f"{SETTINGS_URL}/{PLAIN_KEY}", {"value": "x"}),
    ("delete", f"{SETTINGS_URL}/{PLAIN_KEY}", None),
]


@pytest.mark.parametrize(("method", "url", "body"), REQUESTS)
def test_settings_need_a_login(client, method, url, body):
    kwargs = {} if body is None else {"json": body}

    assert getattr(client, method)(url, **kwargs).status_code == 401


@pytest.mark.parametrize(("method", "url", "body"), REQUESTS)
def test_settings_are_admin_only(client, method, url, body):
    login_as(client, role=Role.MANAGER)
    kwargs = {} if body is None else {"json": body}

    assert getattr(client, method)(url, **kwargs).status_code == 403

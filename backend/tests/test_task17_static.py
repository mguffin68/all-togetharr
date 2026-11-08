"""Task 17a: the API serves the built SPA from STATIC_DIR."""

import pytest
from fastapi.testclient import TestClient

from all_togetharr.main import create_app
from all_togetharr.platform.settings import Settings

INDEX = "<!doctype html><html><body><div id=\"root\"></div></body></html>"
SCRIPT = "console.log('app');"


@pytest.fixture
def static_dir(tmp_path):
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(INDEX)
    (root / "assets" / "app-1234.js").write_text(SCRIPT)
    (root / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("do not serve")
    return root


@pytest.fixture
def spa_client(tmp_path, static_dir):
    settings = Settings(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        static_dir=static_dir,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_static_dir_reads_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    assert Settings().static_dir == tmp_path


def test_static_dir_is_off_by_default(client):
    assert client.app.state.settings.static_dir is None
    assert client.get("/").status_code == 404
    assert client.get("/api/health").status_code == 200


def test_root_serves_index(spa_client):
    response = spa_client.get("/")
    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["content-type"].startswith("text/html")


def test_index_is_not_cached(spa_client):
    response = spa_client.get("/")
    assert response.headers["cache-control"] == "no-cache"


def test_serves_built_assets(spa_client):
    response = spa_client.get("/assets/app-1234.js")
    assert response.status_code == 200
    assert response.text == SCRIPT
    assert "javascript" in response.headers["content-type"]


def test_serves_top_level_files(spa_client):
    response = spa_client.get("/favicon.svg")
    assert response.status_code == 200
    assert response.text == "<svg/>"


@pytest.mark.parametrize("path", ["/titles/7", "/titles/7/", "/settings/users", "/login"])
def test_client_routes_fall_back_to_index(spa_client, path):
    response = spa_client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/assets/missing-5678.js", "/missing.png"])
def test_missing_files_are_404_not_index(spa_client, path):
    response = spa_client.get(path)
    assert response.status_code == 404
    assert response.text != INDEX


@pytest.mark.parametrize("path", ["/api", "/api/", "/api/v1/nope", "/api/nope"])
def test_unknown_api_paths_stay_json_404(spa_client, path):
    response = spa_client.get(path)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.text != INDEX


def test_api_routes_still_work(spa_client):
    assert spa_client.get("/api/health").json()["status"] == "ok"
    assert spa_client.get("/api/v1/auth/setup").json() == {"required": True}


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/assets/%2e%2e/%2e%2e/secret.txt",
        "/..%2fsecret.txt",
    ],
)
def test_does_not_serve_files_outside_static_dir(spa_client, path):
    response = spa_client.get(path)
    assert "do not serve" not in response.text


@pytest.mark.parametrize("path", ["/a%00b", "/titles/%00", "/%00.js", "/" + "a" * 5000])
def test_unusable_paths_are_404_not_500(spa_client, path):
    response = spa_client.get(path)
    assert response.status_code == 404
    assert response.text != INDEX


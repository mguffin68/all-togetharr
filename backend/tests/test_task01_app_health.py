"""Task 1: app factory, health check and API docs."""

from all_togetharr import __version__


def test_health_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "ok"


def test_health_reports_package_version(client):
    assert client.get("/api/health").json()["version"] == __version__


def test_docs_served_at_api_docs(client):
    response = client.get("/api/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_fastapi_default_docs_paths_are_off(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_openapi_spec_lists_health_route(client):
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]

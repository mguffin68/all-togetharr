"""Task 17b: the container entry point starts uvicorn with JSON logging from line one."""

import json
import logging

from all_togetharr import serve


def run_serve(monkeypatch):
    calls: dict = {}

    def fake_run(app, **kwargs):
        calls["app"] = app
        calls.update(kwargs)
        logging.getLogger("uvicorn.error").info("Started server process [1]")

    monkeypatch.setattr(serve.uvicorn, "run", fake_run)
    serve.main()
    return calls


def test_starts_the_app_factory_on_port_8080(monkeypatch):
    calls = run_serve(monkeypatch)

    assert calls["app"] == "all_togetharr.main:create_app"
    assert calls["factory"] is True
    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 8080


def test_disables_uvicorn_log_config(monkeypatch):
    calls = run_serve(monkeypatch)

    assert "log_config" in calls
    assert calls["log_config"] is None


def test_uvicorn_startup_lines_are_json(monkeypatch, capsys):
    run_serve(monkeypatch)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines, "expected uvicorn's startup line on stdout"
    record = json.loads(lines[-1])
    assert record["message"] == "Started server process [1]"
    assert record["logger"] == "uvicorn.error"


def test_respects_log_level(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    run_serve(monkeypatch)

    assert capsys.readouterr().out.strip() == ""

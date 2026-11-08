"""Task 5: structured JSON logs on stdout and request logging."""

import json
import logging
import sys
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from all_togetharr.main import create_app
from all_togetharr.platform.logging import configure_logging

REQUEST_LOGGER = "all_togetharr.request"


def json_lines(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def request_lines(capsys):
    return [line for line in json_lines(capsys) if line["logger"] == REQUEST_LOGGER]


def with_level(settings, level):
    return settings.model_copy(update={"log_level": level})


def test_each_record_is_one_json_object_with_the_core_fields(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("hello")

    (line,) = json_lines(capsys)
    assert line["level"] == "INFO"
    assert line["logger"] == "all_togetharr.test"
    assert line["message"] == "hello"
    assert "time" in line


def test_time_is_iso_8601_in_utc(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("hello")

    (line,) = json_lines(capsys)
    assert datetime.fromisoformat(line["time"]).utcoffset() == timedelta(0)


def test_multi_line_message_stays_on_one_line(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("first\nsecond")

    (line,) = json_lines(capsys)
    assert line["message"] == "first\nsecond"


def test_extra_fields_are_included(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("grabbed", extra={"title_id": 5})

    (line,) = json_lines(capsys)
    assert line["title_id"] == 5


def test_extra_fields_that_are_not_json_do_not_crash(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("odd", extra={"thing": object()})

    (line,) = json_lines(capsys)
    assert "object" in line["thing"]


def test_extra_fields_cannot_replace_core_fields(capsys, settings):
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("hello", extra={"level": "FAKE"})

    (line,) = json_lines(capsys)
    assert line["level"] == "INFO"


def test_uvicorn_color_message_is_dropped(capsys, settings):
    configure_logging(settings)

    logging.getLogger("uvicorn.error").info("up", extra={"color_message": "\x1b[1mup\x1b[0m"})

    (line,) = json_lines(capsys)
    assert "color_message" not in line


def test_other_library_logs_are_not_silenced(capsys, settings):
    configure_logging(settings)

    logging.getLogger("some.library").info("working")

    (line,) = json_lines(capsys)
    assert line["message"] == "working"


def test_http_client_urls_stay_out_of_info_logs(capsys, settings):
    configure_logging(settings)

    logging.getLogger("httpx").info("GET https://api.example/?api_key=secret")
    logging.getLogger("httpcore").info("GET https://api.example/?api_key=secret")

    assert capsys.readouterr().out == ""


def test_http_client_warnings_still_appear(capsys, settings):
    configure_logging(settings)

    logging.getLogger("httpx").warning("connection problem")

    (line,) = json_lines(capsys)
    assert line["message"] == "connection problem"


def test_exceptions_are_logged_with_the_traceback(capsys, settings):
    configure_logging(settings)

    try:
        raise ValueError("bad value")
    except ValueError:
        logging.getLogger("all_togetharr.test").exception("failed")

    (line,) = json_lines(capsys)
    assert line["level"] == "ERROR"
    assert "ValueError: bad value" in line["exception"]


def test_log_level_filters_output(capsys, settings):
    configure_logging(with_level(settings, "WARNING"))
    logger = logging.getLogger("all_togetharr.test")

    logger.info("quiet")
    logger.warning("loud")

    assert [line["message"] for line in json_lines(capsys)] == ["loud"]


def test_configuring_twice_does_not_duplicate_lines(capsys, settings):
    configure_logging(settings)
    configure_logging(settings)

    logging.getLogger("all_togetharr.test").info("once")

    assert len(json_lines(capsys)) == 1


def test_uvicorn_logs_become_json_exactly_once(capsys, settings):
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers[:] = [logging.StreamHandler(sys.stdout)]
    uvicorn_logger.propagate = False
    configure_logging(settings)

    logging.getLogger("uvicorn.error").info("server up")

    (line,) = json_lines(capsys)
    assert line["message"] == "server up"


def test_uvicorn_access_log_is_silent(capsys, settings):
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers[:] = [logging.StreamHandler(sys.stdout)]
    configure_logging(settings)

    access_logger.info("GET / 200")

    assert capsys.readouterr().out == ""


def test_startup_output_is_all_json(capsys, settings):
    with TestClient(create_app(with_level(settings, "DEBUG"))):
        pass

    assert json_lines(capsys) != []


def test_requests_log_method_path_status_and_duration(capsys, settings):
    with TestClient(create_app(settings)) as client:
        client.get("/api/docs")

    (line,) = request_lines(capsys)
    assert line["level"] == "INFO"
    assert line["method"] == "GET"
    assert line["path"] == "/api/docs"
    assert line["status"] == 200
    assert line["duration_ms"] >= 0


def test_query_strings_are_not_logged(capsys, settings):
    with TestClient(create_app(settings)) as client:
        client.get("/api/docs?token=secret-value")

    output = capsys.readouterr().out
    assert "/api/docs" in output
    assert "secret-value" not in output


def test_failed_requests_are_logged_as_500(capsys, settings):
    app = create_app(settings)

    @app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/boom").status_code == 500

    (line,) = request_lines(capsys)
    assert line["path"] == "/boom"
    assert line["status"] == 500


def test_health_checks_are_hidden_at_info(capsys, settings):
    with TestClient(create_app(settings)) as client:
        client.get("/api/health")

    assert request_lines(capsys) == []


def test_health_checks_are_logged_at_debug(capsys, settings):
    with TestClient(create_app(with_level(settings, "DEBUG"))) as client:
        client.get("/api/health")

    (line,) = request_lines(capsys)
    assert line["level"] == "DEBUG"
    assert line["path"] == "/api/health"

import json

from utils_api.logging import setup_logging


def test_setup_logging_outputs_json(capsys):
    logger = setup_logging("test-service", level="INFO", json_logs=True)

    logger.info("hello", extra={"correlation_id": "abc"})

    captured = capsys.readouterr().out.strip()
    parsed = json.loads(captured)

    assert parsed["message"] == "hello"
    assert parsed["service"] == "test-service"
    assert parsed["correlation_id"] == "abc"
    assert parsed["level"] == "INFO"

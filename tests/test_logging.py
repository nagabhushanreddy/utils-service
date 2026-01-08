import json

from utils.logger import get_logger, reset_logging, setup_logging


def teardown_function():
    reset_logging()


def test_setup_logging_outputs_json(capsys, tmp_path):
    log_file = tmp_path / "out.log"
    logging_config = {
        "service_name": "test-service",
        "level": "INFO",
        "file": str(log_file),
    }

    setup_logging(logging_config=logging_config)
    logger = get_logger()
    logger.info("hello", extra={"correlation_id": "abc"})

    captured = capsys.readouterr().out.strip()
    parsed_console = json.loads(captured)

    assert parsed_console["message"] == "hello"
    assert parsed_console["service"] == "test-service"
    assert parsed_console["correlation_id"] == "abc"
    assert parsed_console["level"] == "INFO"

    parsed_file = json.loads(log_file.read_text().strip())
    assert parsed_file["message"] == "hello"
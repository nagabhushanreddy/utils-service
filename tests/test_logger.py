import json
import logging
from pathlib import Path

import pytest

from utils.logger import get_logger, reset_logging, setup_logging


def teardown_function():
    reset_logging()


def test_structured_formatter_includes_service_and_extra(tmp_path):
    log_file = tmp_path / "test.log"
    logging_config = {
        "service_name": "svc",
        "level": "INFO",
        "file": str(log_file),
        "extra_fields": {"env": "test"},
    }

    setup_logging(logging_config=logging_config)
    logger = get_logger()

    logger.info("hello", extra={"user_id": "u1"})

    content = log_file.read_text().strip()
    record = json.loads(content)
    assert record["service"] == "svc"
    assert record["env"] == "test"
    assert record["user_id"] == "u1"
    assert record["message"] == "hello"


def test_setup_logging_accepts_dictconfig(tmp_path):
    log_file = tmp_path / "dc.log"
    dict_cfg = {
        "version": 1,
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "formatter": "basic",
                "filename": str(log_file),
                "encoding": "utf-8",
            }
        },
        "formatters": {"basic": {"format": "%(levelname)s:%(message)s"}},
        "root": {"handlers": ["file"], "level": "INFO"},
    }

    setup_logging(logging_config=dict_cfg)
    logger = logging.getLogger()
    logger.info("hello")
    logging.shutdown()

    assert log_file.exists()
    assert "INFO:hello" in log_file.read_text()


def test_setup_logging_uses_defaults_when_no_config():
    reset_logging()
    setup_logging(service_name="default-svc")
    logger = get_logger()
    logger.info("hi")
    assert logger.name == "default-svc"


def test_get_logger_with_name_uses_active_service():
    reset_logging()
    setup_logging(service_name="svc-x")
    logger = get_logger("custom")
    assert logger.name == "custom"
    root_logger = get_logger()
    assert root_logger.name == "svc-x"

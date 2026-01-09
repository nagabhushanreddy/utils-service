"""Simple tests for the simplified logger."""
import json
import logging
import tempfile
from pathlib import Path

import pytest

from utils.config import config
from utils.logger import get_logger, reset_logging, init_app_logging


def teardown_function():
    reset_logging()


def test_basic_logging_to_file(tmp_path):
    """Test that logging works with file output."""
    # Setup config files
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    app_config = {
        "application": {"name": "test-service"},
        "logging": {
            "level": "INFO",
            "file": str(tmp_path / "logs" / "app.log")
        }
    }
    
    import yaml
    with open(config_dir / "app.yaml", "w") as f:
        yaml.dump(app_config, f)
    
    # Reload config from directory
    config.config_dir = config_dir
    config.reload()
    
    # Setup logging
    logger = init_app_logging()
    logger.info("test message", extra={"user_id": "123"})
    
    # Verify file was created
    log_file = tmp_path / "logs" / "app.log"
    assert log_file.exists()
    
    # Verify JSON content
    content = log_file.read_text().strip()
    record = json.loads(content)
    assert record["message"] == "test message"
    assert record["user_id"] == "123"
    assert record["level"] == "INFO"


def test_dictconfig_support(tmp_path):
    """Test that dictConfig from config works."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    log_file = tmp_path / "dict.log"
    dict_config = {
        "application": {"name": "dict-test"},
        "logging": {
            "version": 1,
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_file),
                    "formatter": "simple"
                }
            },
            "formatters": {
                "simple": {
                    "format": "%(levelname)s:%(message)s"
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["file"]
            }
        }
    }
    
    import yaml
    with open(config_dir / "logging.yaml", "w") as f:
        yaml.dump(dict_config, f)
    
    config.config_dir = config_dir
    config.reload()
    
    logger = init_app_logging()
    logger.info("dictconfig test")
    
    assert log_file.exists()
    assert "INFO:dictconfig test" in log_file.read_text()


def test_get_logger_with_module_name(tmp_path):
    """Test get_logger returns properly namespaced loggers."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    import yaml
    with open(config_dir / "app.yaml", "w") as f:
        yaml.dump({"application": {"name": "myapp"}}, f)
    
    config.config_dir = config_dir
    config.reload()
    
    reset_logging()
    logger = init_app_logging()  # This creates the myapp logger
    
    module_logger = get_logger("database")
    assert module_logger.name == "myapp.database"
    
    assert logger.name == "myapp"


def test_json_formatter_fields(tmp_path):
    """Test that JSON formatter includes all expected fields."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    config_data = {
        "application": {"name": "field-test"},
        "logging": {
            "level": "INFO",
            "file": str(tmp_path / "fields.log")
        }
    }
    
    import yaml
    with open(config_dir / "app.yaml", "w") as f:
        yaml.dump(config_data, f)
    
    config.config_dir = config_dir
    config.reload()
    
    logger = init_app_logging()
    logger.info("field test")
    
    log_file = tmp_path / "fields.log"
    record = json.loads(log_file.read_text().strip())
    
    # Check standard fields
    assert "timestamp" in record
    assert "level" in record
    assert "name" in record
    assert "message" in record
    assert "module" in record
    assert "funcName" in record
    assert "lineno" in record

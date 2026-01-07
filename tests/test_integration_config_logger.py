"""Integration tests for config and logger working together.

This test creates a temporary config directory with YAML/JSON settings and verifies
that the global config singleton loads multiple config files, the logger reads those settings,
and writes structured JSON logs to a file.

Uses pytest fixtures for clean setup/teardown before and after each test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.config import config
from utils.logger import Logger


@pytest.fixture
def temp_config_and_logs(tmp_path: Path):
    """Pytest fixture: Setup temp config/logs dirs before test, restore after.
    
    BEFORE TEST (setup):
    - Create temp config directory with app.yaml and logging.json
    - Point global config singleton to temp directory
    - Reload config to pick up new files
    - Reset logger singleton to reinitialize with new config
    
    AFTER TEST (teardown/cleanup):
    - Restore original config directory
    - Reset logger singleton
    - Reload config (restores original state)
    - tmp_path is automatically cleaned up by pytest
    """
    # BEFORE TEST: Setup
    original_config_dir = config.config_dir
    
    cfg_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    
    # Create app.yaml with application settings
    app_yaml = f"""
application:
  name: "test-integration-service"
  version: "1.0.0"
  environment: "test"
paths:
  logs:
    dir: "{logs_dir}"
    file: "{logs_dir}/app.log"
"""
    (cfg_dir / "app.yaml").write_text(app_yaml)
    
    # Create logging.json with logging configuration
    logging_json = {
        "logging": {
            "level": "INFO",
            "json_format": True,
            "max_bytes": 10 * 1024 * 1024,
            "backup_count": 3,
        }
    }
    (cfg_dir / "logging.json").write_text(json.dumps(logging_json, indent=2))
    
    # Point global config to temp directory and reload
    config.config_dir = cfg_dir
    config.reload()
    
    # Reset logger singleton to reinitialize with new config
    Logger.reset()
    
    # Yield control to test function
    yield cfg_dir, logs_dir
    
    # AFTER TEST: Cleanup (runs after test completes, even if test fails)
    Logger.reset()
    config.config_dir = original_config_dir
    config.reload()
    Logger()  # Reinitialize with original config


def test_config_and_logger_integration(temp_config_and_logs):
    """Test full integration: load config files, create logger, write structured logs.
    
    Uses pytest fixture to handle setup/teardown of config directories and logger singleton.
    
    Verifies:
    1. Config loads both YAML and JSON files
    2. Config values are accessible via dot notation
    3. Singleton logger uses config settings to write structured JSON logs
    4. Log file contains proper JSON with all extra fields
    5. Directories are created by Config from paths configuration
    """
    cfg_dir, logs_dir = temp_config_and_logs
    
    # Assert config files are loaded
    loaded_files = config.list_config_files()
    assert "app.yaml" in loaded_files, f"app.yaml should be loaded, got {loaded_files}"
    assert "logging.json" in loaded_files, f"logging.json should be loaded, got {loaded_files}"
    
    # Assert config values are loaded correctly
    assert config.get("application.name") == "test-integration-service"
    assert config.get("application.version") == "1.0.0"
    assert config.get("logging.level") == "INFO"
    assert config.get("logging.json_format") is True
    
    # Get singleton logger (reinitialized with new config by fixture)
    logger = Logger()
    
    # Write structured log messages
    logger.info("Integration test started", extra={"test_id": "test_001"})
    logger.warning("Test warning", extra={"severity": "medium"})
    logger.info("Integration test completed", extra={"test_id": "test_001", "status": "success"})
    
    # Verify log file exists and contains structured JSON
    log_file = logs_dir / "app.log"
    assert log_file.exists(), f"Log file should exist at {log_file}"
    
    log_content = log_file.read_text().strip()
    assert log_content, "Log file should not be empty"
    
    log_lines = log_content.split('\n')
    assert len(log_lines) >= 3, f"Should have at least 3 log entries, got {len(log_lines)}"
    
    # Parse and validate each JSON log entry
    log1 = json.loads(log_lines[0])
    assert log1["message"] == "Integration test started"
    assert log1["level"] == "INFO"
    assert log1["service"] == "test-integration-service"
    assert log1["test_id"] == "test_001"
    assert "timestamp" in log1
    assert "logger" in log1
    
    log2 = json.loads(log_lines[1])
    assert log2["message"] == "Test warning"
    assert log2["level"] == "WARNING"
    assert log2["severity"] == "medium"
    
    log3 = json.loads(log_lines[2])
    assert log3["message"] == "Integration test completed"
    assert log3["status"] == "success"
    
    # Verify directories were created by Config
    assert logs_dir.exists(), "Logs directory should be created by Config"

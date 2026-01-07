"""Tests for logger module."""

import json
import logging
import tempfile
from pathlib import Path

import pytest

from utils.logger import (
    DetailedFormatter,
    JsonFormatter,
    get_logger,
    setup_logging,
    setup_global_logger,
)


class TestJsonFormatter:
    """Test JSON formatter."""

    def test_basic_formatting(self):
        """Test basic JSON log formatting."""
        formatter = JsonFormatter(service_name="test-service")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["service"] == "test-service"
        assert parsed["message"] == "Test message"
        assert parsed["line"] == 42
        assert "timestamp" in parsed

    def test_extra_fields(self):
        """Test formatter with extra fields."""
        formatter = JsonFormatter(
            service_name="test-service",
            extra_fields={"environment": "test", "version": "1.0.0"}
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["environment"] == "test"
        assert parsed["version"] == "1.0.0"

    def test_custom_attributes(self):
        """Test logging with custom attributes via extra parameter."""
        formatter = JsonFormatter(service_name="test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Message",
            args=(),
            exc_info=None,
        )
        record.user_id = "12345"
        record.request_id = "abc-def"
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["user_id"] == "12345"
        assert parsed["request_id"] == "abc-def"

    def test_exception_formatting(self):
        """Test exception formatting in JSON logs."""
        formatter = JsonFormatter(service_name="test-service")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert "exc_info" in parsed
        assert "ValueError" in parsed["exc_info"]
        assert parsed["exc_type"] == "ValueError"


class TestDetailedFormatter:
    """Test detailed formatter."""

    def test_detailed_format(self):
        """Test detailed formatting includes file and line."""
        formatter = DetailedFormatter(detailed=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        assert "INFO" in output
        assert "test.logger" in output
        assert "Test message" in output
        assert "test.py:42" in output

    def test_simple_format(self):
        """Test simple formatting without file/line details."""
        formatter = DetailedFormatter(detailed=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        
        output = formatter.format(record)
        
        assert "WARNING" in output
        assert "test.logger" in output
        assert "Warning message" in output


class TestSetupLogging:
    """Test setup_logging function."""

    def test_basic_setup(self):
        """Test basic logger setup."""
        logger = setup_logging(
            service_name="test-app",
            level="DEBUG",
            use_config=False,
        )
        
        assert logger.name == "test-app"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1  # Console handler

    def test_json_logs(self):
        """Test JSON log formatting."""
        logger = setup_logging(
            service_name="test-app",
            json_logs=True,
            use_config=False,
        )
        
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_file_logging(self):
        """Test file logging with rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            logger = setup_logging(
                service_name="test-app",
                log_file=log_file,
                max_bytes=1024,
                backup_count=3,
                use_config=False,
            )
            
            assert len(logger.handlers) == 2  # Console + File
            assert log_file.exists()
            
            # Test writing logs
            logger.info("Test message")
            
            content = log_file.read_text()
            assert "Test message" in content

    def test_json_file_logging(self):
        """Test JSON formatting to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            logger = setup_logging(
                service_name="test-app",
                json_logs=True,
                log_file=log_file,
                use_config=False,
            )
            
            logger.info("JSON test", extra={"user_id": "123"})
            
            content = log_file.read_text()
            parsed = json.loads(content.strip())
            
            assert parsed["message"] == "JSON test"
            assert parsed["user_id"] == "123"
            assert parsed["service"] == "test-app"

    def test_extra_fields(self):
        """Test default extra fields in logs."""
        logger = setup_logging(
            service_name="test-app",
            json_logs=True,
            extra_fields={"env": "test", "region": "us-east"},
            use_config=False,
        )
        
        # Get the formatter from handler
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)
        assert handler.formatter.extra_fields["env"] == "test"
        assert handler.formatter.extra_fields["region"] == "us-east"


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_simple(self):
        """Test getting a simple logger."""
        logger = get_logger("myapp")
        assert logger.name == "myapp"

    def test_get_logger_with_module(self):
        """Test getting logger with module name."""
        logger = get_logger("myapp", "database")
        assert logger.name == "myapp.database"

    def test_get_logger_root(self):
        """Test getting root logger."""
        logger = get_logger()
        assert logger.name == "root"


class TestLoggerIntegration:
    """Integration tests for logger module."""

    def test_structured_logging(self):
        """Test structured logging with extra fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "structured.log"
            
            logger = setup_logging(
                service_name="api",
                json_logs=True,
                log_file=log_file,
                use_config=False,
            )
            
            # Log with structured data
            logger.info(
                "User login",
                extra={
                    "user_id": "user_123",
                    "ip_address": "192.168.1.1",
                    "action": "login",
                }
            )
            
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "user_id": "user_456",
                    "endpoint": "/api/data",
                    "attempts": 100,
                }
            )
            
            # Read and parse logs
            lines = log_file.read_text().strip().split('\n')
            assert len(lines) == 2
            
            log1 = json.loads(lines[0])
            assert log1["message"] == "User login"
            assert log1["user_id"] == "user_123"
            assert log1["action"] == "login"
            
            log2 = json.loads(lines[1])
            assert log2["message"] == "Rate limit exceeded"
            assert log2["attempts"] == 100
            assert log2["level"] == "WARNING"

    def test_multi_handler_logging(self):
        """Test logging to both console and file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "multi.log"
            
            logger = setup_logging(
                service_name="test",
                level="INFO",
                log_file=log_file,
                use_config=False,
            )
            
            logger.info("Test message")
            logger.error("Error message")
            
            # Verify file has both messages
            content = log_file.read_text()
            assert "Test message" in content
            assert "Error message" in content

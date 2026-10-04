"""
Unit tests for structured application logging and JSONLogFormatter.
Validates OBS-LOG-001-STRUCTURED-LOGGING requirements.
"""

import ast
import json
import logging
import os
import sys

from app.core.config import settings
from app.core.logging import JSONLogFormatter, setup_logging


def test_json_log_formatter_format():
    """Verify JSONLogFormatter formats records as structured JSON."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test_module",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test message with param: %s",
        args=("value1",),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["level"] == "INFO"
    assert data["module"] == "test_module"
    assert data["message"] == "Test message with param: value1"
    assert "timestamp" in data
    assert "exception" not in data


def test_json_log_formatter_with_exception():
    """Verify JSONLogFormatter includes formatted exception if exc_info exists."""
    formatter = JSONLogFormatter()
    try:
        raise ValueError("test error message")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="error_module",
        level=logging.ERROR,
        pathname=__file__,
        lineno=25,
        msg="Something failed",
        args=(),
        exc_info=exc_info,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data["level"] == "ERROR"
    assert data["module"] == "error_module"
    assert data["message"] == "Something failed"
    assert "exception" in data
    assert "ValueError: test error message" in data["exception"]


def test_setup_logging_production(monkeypatch):
    """Verify setup_logging configures JSONLogFormatter when ENVIRONMENT is production."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    setup_logging()

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, JSONLogFormatter)


def test_setup_logging_non_production(monkeypatch):
    """Verify setup_logging configures standard formatter when ENVIRONMENT is not production."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    setup_logging()

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0
    handler = root_logger.handlers[0]
    assert not isinstance(handler.formatter, JSONLogFormatter)


def test_no_raw_print_in_app():
    """Verify no active print() calls remain across app/ python files using AST inspection."""
    app_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")
    found_prints = []

    for root, _, files in os.walk(app_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                    found_prints.append(f"{path}:{node.lineno}")

    assert not found_prints, f"Found print calls in application code: {found_prints}"

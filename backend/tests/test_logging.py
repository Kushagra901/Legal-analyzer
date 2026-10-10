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


def test_module_structured_loggers_initialized():
    """Verify target modules and routers initialize standard logging.Logger instances."""
    from app.api.v1.routers import documents
    from app.api.v1.routers.documents import analysis, chat, crud, review
    from app.services import ocr_service, storage_service

    assert isinstance(documents.logger, logging.Logger)
    assert isinstance(crud.logger, logging.Logger)
    assert isinstance(analysis.logger, logging.Logger)
    assert isinstance(review.logger, logging.Logger)
    assert isinstance(chat.logger, logging.Logger)
    assert isinstance(storage_service.logger, logging.Logger)
    assert isinstance(ocr_service.logger, logging.Logger)


def test_storage_service_structured_logging(caplog, monkeypatch):
    """Verify storage_service logs warnings when unconfigured and info on mock upload."""
    from app.services.storage_service import StorageService

    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    with caplog.at_level(logging.INFO):
        svc = StorageService()
        assert any(
            rec.levelno == logging.WARNING and "StorageService initialized in mock mode" in rec.message
            for rec in caplog.records
        )
        svc.upload_file(b"dummy-bytes", "test.pdf", "application/pdf")
        assert any(
            rec.levelno == logging.INFO and "StorageService in mock mode. Skipping upload" in rec.message
            for rec in caplog.records
        )


def test_ocr_service_structured_logging(caplog):
    """Verify ocr_service logs informational format detection and caught warnings."""
    from app.services.ocr_service import OCRService

    svc = OCRService()
    with caplog.at_level(logging.INFO):
        svc.process_document(b"Sample plain text document for testing.")
        assert any(
            rec.levelno == logging.INFO and "Processing document with detected format" in rec.message
            for rec in caplog.records
        )

        # Trigger warning in detect_format with invalid path
        svc.detect_format("non_existent_file_path_for_testing.xyz")
        assert any(
            rec.levelno == logging.WARNING and "Failed to read header from" in rec.message
            for rec in caplog.records
        )


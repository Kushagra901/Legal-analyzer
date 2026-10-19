"""
Unit tests for structured JSON logging, trace ID correlation middleware,
binary payload sanitization, and background task / n8n webhook propagation.
"""

import json
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routers.documents.crud import trigger_n8n_webhook
from app.core.config import settings
from app.core.logging import (
    JSONLogFormatter,
    StructuredLogger,
    get_logger,
    sanitize_binary_data,
)
from app.core.tracing import (
    clear_trace_id,
    get_trace_id,
    is_valid_trace_id,
    resolve_trace_id,
    set_trace_id,
)
from app.main import app

client = TestClient(app)


# =============================================================================
# Edge Case 1: Missing or Malformed X-Trace-ID Headers
# =============================================================================


def test_is_valid_trace_id_validation():
    """Verify trace ID validation logic for safe, bounded, non-empty identifiers."""
    assert is_valid_trace_id("valid-trace-id-1234") is True
    assert is_valid_trace_id(str(uuid.uuid4())) is True
    assert is_valid_trace_id("service.trace_42:xyz") is True

    # Missing, empty, or whitespace
    assert is_valid_trace_id(None) is False
    assert is_valid_trace_id("") is False
    assert is_valid_trace_id("   ") is False
    assert is_valid_trace_id(12345) is False

    # Malformed with control characters, newlines, spaces, or excessive length
    assert is_valid_trace_id("bad\nid") is False
    assert is_valid_trace_id("bad\rid") is False
    assert is_valid_trace_id("bad id with spaces") is False
    assert is_valid_trace_id("<script>") is False
    assert is_valid_trace_id("a" * 129) is False


def test_resolve_trace_id_generates_on_invalid():
    """Verify resolve_trace_id produces a fresh UUIDv4 when input is invalid or missing."""
    valid_id = "my-custom-trace-id"
    assert resolve_trace_id(valid_id) == valid_id

    # Test that missing or malformed inputs yield valid UUIDs
    for bad_input in [None, "", "   ", "malformed\nline", "a" * 200]:
        resolved = resolve_trace_id(bad_input)
        assert is_valid_trace_id(resolved) is True
        # Verify it parses as UUIDv4
        parsed = uuid.UUID(resolved)
        assert str(parsed) == resolved


def test_middleware_generates_trace_id_when_missing():
    """Verify that requests without X-Trace-ID receive a generated UUIDv4 in response headers."""
    response = client.get("/health")
    assert response.status_code == 200
    trace_id = response.headers.get("x-trace-id")
    assert trace_id is not None
    parsed = uuid.UUID(trace_id)
    assert str(parsed) == trace_id
    # Also verify backward-compatible X-Request-ID matches
    assert response.headers.get("x-request-id") == trace_id


def test_middleware_preserves_valid_trace_id():
    """Verify that incoming valid X-Trace-ID is preserved and returned in the response."""
    custom_trace = "client-trace-550e8400-e29b-41d4-a716-446655440000"
    response = client.get("/health", headers={"X-Trace-ID": custom_trace})
    assert response.status_code == 200
    assert response.headers.get("x-trace-id") == custom_trace
    assert response.headers.get("x-request-id") == custom_trace


def test_middleware_rejects_malformed_trace_id_and_generates_new():
    """Verify that incoming malformed X-Trace-ID (e.g., with newlines or spaces) is replaced with a clean UUID."""
    malformed_headers = [
        "bad\ninjection-attempt",
        "spaces are not allowed",
        "x" * 200,
        "   ",
    ]
    for bad_header in malformed_headers:
        response = client.get("/health", headers={"X-Trace-ID": bad_header})
        assert response.status_code == 200
        assigned = response.headers.get("x-trace-id")
        assert assigned is not None
        assert assigned != bad_header
        # Must be valid UUID
        parsed = uuid.UUID(assigned)
        assert str(parsed) == assigned


# =============================================================================
# Edge Case 2: Logging Binary File Uploads (Safe Sanitization)
# =============================================================================


def test_sanitize_binary_data_primitives():
    """Verify bytes, bytearray, memoryview, and binary strings are replaced with summaries."""
    assert sanitize_binary_data(b"%PDF-1.4 binary content") == "<binary data: 23 bytes>"
    assert sanitize_binary_data(bytearray(b"abc12345")) == "<binary data: 8 bytes>"
    assert sanitize_binary_data(memoryview(b"1234")) == "<binary data: 4 bytes>"
    assert sanitize_binary_data("hello\x00world") == "<binary string: 11 chars>"
    assert sanitize_binary_data("regular text") == "regular text"
    assert sanitize_binary_data(12345) == 12345


def test_sanitize_binary_data_nested_structures():
    """Verify recursive sanitization inside dictionaries, lists, and tuples."""
    payload = {
        "filename": "sample.pdf",
        "file_bytes": b"%PDF-dummy",
        "details": {
            "raw_signature": bytearray(b"\x89PNG\r\n"),
            "text": "clean string",
        },
        "chunks": [b"chunk1", "clean chunk", b"chunk2"],
    }
    sanitized = sanitize_binary_data(payload)

    assert sanitized["filename"] == "sample.pdf"
    assert sanitized["file_bytes"] == "<binary data: 10 bytes>"
    assert sanitized["details"]["raw_signature"] == "<binary data: 6 bytes>"
    assert sanitized["details"]["text"] == "clean string"
    assert sanitized["chunks"] == ["<binary data: 6 bytes>", "clean chunk", "<binary data: 6 bytes>"]


def test_json_formatter_sanitizes_binary_log_records():
    """Verify JSONLogFormatter strips raw bytes from log output and produces valid JSON."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test_upload_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=100,
        msg="File uploaded successfully",
        args=(),
        exc_info=None,
    )
    record.document_id = "doc-uuid-1234"
    record.raw_content = b"%PDF-1.4\n%BinaryBlob\x00\x01\x02\x03"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["module"] == "test_upload_logger"
    assert parsed["message"] == "File uploaded successfully"
    assert parsed["document_id"] == "doc-uuid-1234"
    assert parsed["raw_content"] == "<binary data: 24 bytes>"
    assert "BinaryBlob" not in formatted


# =============================================================================
# Edge Case 3: Propagation to Background Tasks and Outbound n8n Calls
# =============================================================================


@pytest.mark.anyio
async def test_trigger_n8n_webhook_propagates_explicit_trace_id():
    """Verify trigger_n8n_webhook passes explicit trace_id in X-Trace-ID header."""
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        custom_trace = "trace-n8n-explicit-123"
        await trigger_n8n_webhook(
            document_id="doc-999",
            filename="contract.pdf",
            email="lawyer@example.com",
            trace_id=custom_trace,
        )

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs
        headers = call_kwargs["headers"]

        assert headers.get("X-Trace-ID") == custom_trace
        assert headers.get("X-Request-ID") == custom_trace
        assert headers.get("X-Webhook-Secret") == settings.INTERNAL_SERVICE_TOKEN


@pytest.mark.anyio
async def test_trigger_n8n_webhook_inherits_ambient_context_trace_id():
    """Verify trigger_n8n_webhook inherits ambient trace_id from execution context when omitted."""
    ambient_trace = "trace-ambient-from-middleware-777"
    set_trace_id(ambient_trace)

    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await trigger_n8n_webhook(
                document_id="doc-888",
                filename="nda.pdf",
                email="test@example.com",
            )

            call_kwargs = mock_client.post.call_args.kwargs
            headers = call_kwargs["headers"]
            assert headers.get("X-Trace-ID") == ambient_trace
    finally:
        clear_trace_id()


def test_background_task_trace_id_propagation():
    """Verify that execute_document_analysis binds and uses trace_id in execution context."""
    from app.workers.tasks import execute_document_analysis

    target_trace = "trace-bg-worker-999"
    with patch("app.workers.tasks.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        # Document not found will trigger early exit after setting trace_id
        mock_session.query.return_value.filter.return_value.first.return_value = None

        execute_document_analysis("00000000-0000-0000-0000-000000000000", trace_id=target_trace)

        assert get_trace_id() == target_trace
        clear_trace_id()


# =============================================================================
# Structured Logging & StructuredLogger Verification
# =============================================================================


def test_structured_logger_binding_and_kwargs():
    """Verify StructuredLogger supports .bind() context and keyword arguments."""
    logger = get_logger("test.structured.binding")
    assert isinstance(logger, logging.Logger)
    assert isinstance(logger, StructuredLogger)

    bound = logger.bind(service="legal_analysis", document_id="doc-bound-1")
    assert bound._bound_context["service"] == "legal_analysis"
    assert bound._bound_context["document_id"] == "doc-bound-1"


def test_json_log_formatter_includes_active_trace_id():
    """Verify JSONLogFormatter automatically injects active contextvar trace_id into JSON output."""
    formatter = JSONLogFormatter()
    test_trace = "trace-active-json-test"
    set_trace_id(test_trace)

    try:
        record = logging.LogRecord(
            name="test_trace_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=200,
            msg="Testing trace injection in log line",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["trace_id"] == test_trace
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Testing trace injection in log line"
    finally:
        clear_trace_id()

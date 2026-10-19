"""
Distributed Tracing and Correlation Management.
Provides contextvars-backed trace ID propagation across HTTP requests,
background workers, and outbound third-party integrations (e.g. n8n).
"""

import re
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Trace and correlation header constants
TRACE_ID_HEADER = "X-Trace-ID"
REQUEST_ID_HEADER = "X-Request-ID"

# Regular expression enforcing safe trace identifiers:
# 1-128 alphanumeric characters with hyphens, underscores, dots, or colons.
VALID_TRACE_REGEX = re.compile(r"^[A-Za-z0-9_\-\.:]{1,128}$")

# Context variable holding the active trace ID for the current async execution context
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def is_valid_trace_id(candidate: Any) -> bool:
    """
    Validate that a trace ID is non-empty, within size bounds, and contains only safe characters.

    Args:
        candidate: The value to validate.

    Returns:
        bool: True if candidate is a valid trace ID string, False otherwise.
    """
    if not candidate or not isinstance(candidate, str):
        return False
    trimmed = candidate.strip()
    return bool(VALID_TRACE_REGEX.match(trimmed))


def generate_trace_id() -> str:
    """
    Generate a new random UUIDv4 string for request tracing.

    Returns:
        str: A fresh UUIDv4 string representation.
    """
    return str(uuid.uuid4())


def resolve_trace_id(candidate: Any) -> str:
    """
    Resolves a candidate trace ID string. If the candidate is missing, empty,
    or malformed (e.g., contains control chars or exceeds length limits),
    a new UUIDv4 trace ID is safely generated.

    Args:
        candidate: Incoming candidate trace ID from HTTP headers or context.

    Returns:
        str: A guaranteed valid trace identifier.
    """
    if is_valid_trace_id(candidate):
        return str(candidate).strip()
    return generate_trace_id()


def get_trace_id() -> str | None:
    """
    Retrieve the trace ID from the current async execution context.

    Returns:
        str | None: The active trace ID, or None if not set.
    """
    return _trace_id_var.get()


def set_trace_id(trace_id: str | None) -> str:
    """
    Set the active trace ID in the execution context and bind it to structlog.

    Args:
        trace_id: The trace identifier to set, or None to generate one.

    Returns:
        str: The resolved active trace ID.
    """
    resolved = resolve_trace_id(trace_id)
    _trace_id_var.set(resolved)
    try:
        structlog.contextvars.bind_contextvars(trace_id=resolved)
    except Exception:
        # Fallback if structlog is not initialized yet
        pass
    return resolved


def clear_trace_id() -> None:
    """
    Clear the active trace ID from the execution context and unbind from structlog.
    """
    _trace_id_var.set(None)
    try:
        structlog.contextvars.unbind_contextvars("trace_id")
    except Exception:
        pass

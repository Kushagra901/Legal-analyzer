"""
Request & Trace ID Middleware.
Injects a unique correlation and trace identifier (X-Trace-ID / X-Request-ID) into incoming requests,
context variables, structured loggers, and response headers for distributed tracing.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.tracing import (
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    clear_trace_id,
    is_valid_trace_id,
    resolve_trace_id,
    set_trace_id,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates a unique correlation ID (X-Trace-ID / X-Request-ID)
    for each incoming request and sets it in the request state, contextvars, and response headers.
    Handles missing or malformed trace headers gracefully by generating a clean UUIDv4.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process the incoming request, assigning validated X-Trace-ID and X-Request-ID headers.
        """
        raw_header = request.headers.get(TRACE_ID_HEADER) or request.headers.get(REQUEST_ID_HEADER)

        # Validate header. If missing, blank, or containing invalid characters, resolve_trace_id
        # generates a new UUIDv4 trace ID.
        if is_valid_trace_id(raw_header):
            trace_id = str(raw_header).strip()
        else:
            trace_id = resolve_trace_id(None)

        # Set in execution context and structlog contextvars
        set_trace_id(trace_id)

        # Set on request state for backwards and forward compatibility
        request.state.trace_id = trace_id
        request.state.request_id = trace_id

        try:
            response = await call_next(request)
            response.headers[TRACE_ID_HEADER] = trace_id
            response.headers[REQUEST_ID_HEADER] = trace_id
            return response
        finally:
            clear_trace_id()

"""
Request ID Middleware.
Injects a unique request identifier (X-Request-ID) into incoming requests and response headers
for distributed tracing and request correlation.
"""

from collections.abc import Awaitable, Callable
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates a unique correlation ID (X-Request-ID)
    for each incoming request and sets it in the request state and response headers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process the request, assigning an X-Request-ID header to request state and response.
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

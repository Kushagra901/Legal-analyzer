"""
Rate Limiter configuration and internal service exemption utilities using slowapi.
Provides in-memory storage, client IP resolution, internal token bypass for n8n,
and custom HTTP 429 JSON response handlers.
"""

import hmac
import logging

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from X-Forwarded-For header or direct client host.
    Falls back to '127.0.0.1' if client host is unavailable.

    Args:
        request: The incoming FastAPI HTTP request.

    Returns:
        str: Resolvable IP address string for rate limiting key identification.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and forwarded.strip():
        # First entry in X-Forwarded-For is the originating client IP
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def is_internal_service_request(request: Request) -> bool:
    """
    Determine whether an incoming request originates from an authorized internal service (such as n8n).
    Checks the case-insensitive X-Internal-Token header against settings.INTERNAL_SERVICE_TOKEN
    using constant-time comparison to prevent timing attacks.

    Args:
        request: The incoming FastAPI HTTP request.

    Returns:
        bool: True if request carries a valid internal service token, False otherwise.
    """
    if not hasattr(request, "headers") or request.headers is None:
        return False

    internal_token = request.headers.get("x-internal-token")
    if internal_token is None:
        internal_token = request.headers.get("X-Internal-Token")

    if not internal_token or not settings.INTERNAL_SERVICE_TOKEN:
        return False

    return hmac.compare_digest(internal_token, settings.INTERNAL_SERVICE_TOKEN)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Standard HTTP 429 Too Many Requests response handler for rate limit violations.
    Returns a standardized JSON error response containing clear detail and error keys,
    along with injected rate limit headers.

    Args:
        request: The FastAPI HTTP request that exceeded its limit.
        exc: The RateLimitExceeded exception instance containing limit details.

    Returns:
        Response: A JSONResponse with HTTP 429 status code and structured error body.
    """
    logger.warning(
        "Rate limit exceeded for client %s on %s %s: %s",
        get_client_ip(request),
        request.method,
        request.url.path,
        exc.detail,
    )

    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": f"Rate limit exceeded: {exc.detail}",
            "detail": f"Rate limit exceeded: {exc.detail}",
        },
    )

    if hasattr(request.app.state, "limiter"):
        response = request.app.state.limiter._inject_headers(
            response, getattr(request.state, "view_rate_limit", None)
        )

    return response


# Initialize the rate limiter with explicit in-memory storage (memory://)
# so it operates locally without external Redis dependencies.
limiter: Limiter = Limiter(
    key_func=get_client_ip,
    storage_uri="memory://",
    headers_enabled=False,
)

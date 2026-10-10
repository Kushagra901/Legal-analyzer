"""
Tests for Security Headers Middleware and Rate Limiter configuration.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_security_headers_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("Content-Security-Policy") == "default-src 'self'"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert (
        response.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )
    assert (
        response.headers.get("Referrer-Policy")
        == "strict-origin-when-cross-origin"
    )
    assert (
        response.headers.get("Permissions-Policy")
        == "camera=(), microphone=(), geolocation=(), payment=()"
    )


def test_auth_rate_limiting():
    responses = []
    for _ in range(15):
        res = client.post("/api/v1/auth/login")
        responses.append(res.status_code)

    assert 429 in responses


def test_cors_preflight_allowed():
    """
    Ensure preflight OPTIONS with allowed origin, method, and headers succeeds with strict CORS headers.
    """
    from app.core.config import settings

    response = client.options(
        "/health",
        headers={
            "Origin": settings.FRONTEND_URL,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type, X-Request-ID, X-Internal-Token",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == settings.FRONTEND_URL
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert response.headers.get("access-control-max-age") == "600"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    for m in ["GET", "POST", "PUT", "DELETE", "OPTIONS"]:
        assert m in allow_methods


def test_cors_preflight_disallowed_origin():
    """
    Ensure requests from untrusted origins do not receive allow-origin header.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": "https://malicious-site.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None


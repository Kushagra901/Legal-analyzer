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


def test_auth_rate_limiting():
    responses = []
    for _ in range(15):
        res = client.post("/api/v1/auth/login")
        responses.append(res.status_code)

    assert 429 in responses

"""
Unit and integration tests for API Rate Limiting using slowapi.
Tests strict 5 req/min on document upload, 10 req/min on document chat,
in-memory backend operation, HTTP 429 JSON response structure,
client IP isolation, and internal n8n service exemption via X-Internal-Token.
"""

import asyncio
import io
import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from limits.storage.memory import MemoryStorage
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routers.documents.crud import trigger_n8n_webhook
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.limiter import (
    get_client_ip,
    is_internal_service_request,
    limiter,
    rate_limit_exceeded_handler,
)
from app.main import app
from app.models import Document, Organization, User

# 1. Setup SQLite in-memory database engine for isolated testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_ORG_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TEST_DOC_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def override_get_db() -> Generator[Session, None, None]:
    """Dependency override providing an isolated SQLite in-memory session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user() -> User:
    """Dependency override providing a standard authenticated test user."""
    return User(
        id=TEST_USER_ID,
        org_id=TEST_ORG_ID,
        email="test_ratelimit@example.com",
        role="user",
    )


@pytest.fixture(autouse=True)
def setup_test_db_and_limiter():
    """Seed test fixtures, reset limiter, and clean up after each test."""
    limiter.reset()
    db = TestingSessionLocal()

    # Seed organization, user, and document
    org = db.query(Organization).filter(Organization.id == TEST_ORG_ID).first()
    if not org:
        org = Organization(id=TEST_ORG_ID, name="RateLimit Test Org")
        db.add(org)

    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    if not user:
        user = User(
            id=TEST_USER_ID,
            org_id=TEST_ORG_ID,
            email="test_ratelimit@example.com",
            role="user",
        )
        db.add(user)

    doc = db.query(Document).filter(Document.id == TEST_DOC_ID).first()
    if not doc:
        doc = Document(
            id=TEST_DOC_ID,
            user_id=TEST_USER_ID,
            filename="sample_contract.pdf",
            status="completed",
        )
        db.add(doc)

    db.commit()
    db.close()

    yield

    limiter.reset()


client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests: Limiter Backend, IP Extraction & Exemption Logic
# ---------------------------------------------------------------------------


def test_limiter_in_memory_backend():
    """Verify rate limiter operates via in-memory storage without Redis dependency."""
    storage = limiter._limiter.storage
    assert isinstance(storage, MemoryStorage), f"Expected MemoryStorage, got {type(storage)}"
    # Verify limiter reset functions without exception
    limiter.reset()


def test_get_client_ip_edge_cases():
    """Test get_client_ip handling of X-Forwarded-For, client host, and missing IP."""
    # 1. Single IP in X-Forwarded-For
    req1 = MagicMock(spec=Request)
    req1.headers = {"x-forwarded-for": "203.0.113.195"}
    assert get_client_ip(req1) == "203.0.113.195"

    # 2. Multi-hop comma-separated IPs in X-Forwarded-For (originating client is first)
    req2 = MagicMock(spec=Request)
    req2.headers = {"x-forwarded-for": "198.51.100.10, 10.0.0.1, 172.16.0.1"}
    assert get_client_ip(req2) == "198.51.100.10"

    # 3. Empty or whitespace X-Forwarded-For falls back to client.host
    req3 = MagicMock(spec=Request)
    req3.headers = {"x-forwarded-for": "   "}
    req3.client.host = "192.168.1.50"
    assert get_client_ip(req3) == "192.168.1.50"

    # 4. No header and no client object falls back to 127.0.0.1
    req4 = MagicMock(spec=Request)
    req4.headers = {}
    req4.client = None
    assert get_client_ip(req4) == "127.0.0.1"


def test_is_internal_service_request_edge_cases():
    """Test is_internal_service_request validation across valid, invalid, and empty tokens."""
    valid_token = settings.INTERNAL_SERVICE_TOKEN or "placeholder_internal_service_token_change_me"

    # 1. Valid matching token
    req_valid = MagicMock(spec=Request)
    req_valid.headers = {"x-internal-token": valid_token}
    assert is_internal_service_request(req_valid) is True

    # 2. Case-insensitive header lookup
    req_case = MagicMock(spec=Request)
    req_case.headers = {"X-Internal-Token": valid_token}
    assert is_internal_service_request(req_case) is True

    # 3. Mismatched invalid token
    req_invalid = MagicMock(spec=Request)
    req_invalid.headers = {"x-internal-token": "unauthorized-token-xyz"}
    assert is_internal_service_request(req_invalid) is False

    # 4. Missing header (None)
    req_none = MagicMock(spec=Request)
    req_none.headers = {}
    assert is_internal_service_request(req_none) is False

    # 5. Empty token string
    req_empty = MagicMock(spec=Request)
    req_empty.headers = {"x-internal-token": ""}
    assert is_internal_service_request(req_empty) is False


def test_rate_limit_exceeded_handler_structure():
    """Verify HTTP 429 JSON response payload structure and status code."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}
    mock_request.client = None
    mock_request.method = "POST"
    mock_request.url.path = "/api/v1/documents"
    mock_request.state = MagicMock()
    mock_request.state.view_rate_limit = None
    mock_request.app.state.limiter = limiter

    mock_exc = MagicMock(spec=RateLimitExceeded)
    mock_exc.detail = "5 per 1 minute"
    response = rate_limit_exceeded_handler(mock_request, mock_exc)

    assert response.status_code == 429
    import json
    body = json.loads(response.body.decode("utf-8"))
    assert "Rate limit exceeded: 5 per 1 minute" in body["error"]
    assert "Rate limit exceeded: 5 per 1 minute" in body["detail"]


# ---------------------------------------------------------------------------
# Integration Tests: Endpoint Rate Limits & n8n Exemption
# ---------------------------------------------------------------------------


def test_upload_endpoint_rate_limiting_5_per_minute():
    """
    Ensure POST /api/v1/documents permits exactly 5 rapid requests per minute
    and rejects the 6th request with HTTP 429 Too Many Requests.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test.pdf"),
            patch("app.services.ocr_service.OCRService.process_document", return_value=("Mock contract text content", "native", 1.0)),
            patch("app.api.v1.routers.documents.trigger_n8n_webhook"),
        ):

            responses = []
            for i in range(6):
                file_content = b"%PDF-1.4 mock content for upload test"
                res = client.post(
                    "/api/v1/documents",
                    files={"file": (f"test_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                    headers={"Authorization": "Bearer mock-token"},
                )
                responses.append(res)

            # First 5 requests must succeed (HTTP 200)
            for i in range(5):
                assert responses[i].status_code == 200, (
                    f"Request {i+1} failed with status {responses[i].status_code}: {responses[i].text}"
                )

            # 6th request must be rate limited with HTTP 429
            assert responses[5].status_code == 429, (
                f"Expected 6th request to be 429, got {responses[5].status_code}: {responses[5].text}"
            )
            body = responses[5].json()
            assert "Rate limit exceeded" in body["error"]
            assert "Rate limit exceeded" in body["detail"]
    finally:
        app.dependency_overrides.clear()


def test_upload_endpoint_n8n_internal_token_exemption():
    """
    Ensure internal service calls carrying a valid X-Internal-Token (e.g. from n8n)
    bypass the upload rate limit and are not blocked even after 6+ rapid calls.
    """
    app.dependency_overrides[get_db] = override_get_db

    valid_token = settings.INTERNAL_SERVICE_TOKEN or "placeholder_internal_service_token_change_me"

    try:
        with (
            patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test.pdf"),
            patch("app.services.ocr_service.OCRService.process_document", return_value=("Mock contract text content", "native", 1.0)),
            patch("app.api.v1.routers.documents.trigger_n8n_webhook"),
        ):

            # Execute 8 rapid requests (more than the 5/min limit)
            for i in range(8):
                file_content = b"%PDF-1.4 mock content for n8n upload"
                res = client.post(
                    "/api/v1/documents",
                    files={"file": (f"n8n_doc_{i}.pdf", io.BytesIO(file_content), "application/pdf")},
                    headers={"X-Internal-Token": valid_token},
                )
                assert res.status_code == 200, (
                    f"Internal request {i+1} was unexpectedly throttled: status {res.status_code}, {res.text}"
                )
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_rate_limiting_10_per_minute():
    """
    Ensure POST /api/v1/documents/{document_id}/chat permits exactly 10 rapid requests per minute
    and rejects the 11th request with HTTP 429 Too Many Requests.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch("app.api.v1.routers.documents.chat.EmbeddingService") as mock_embed,
            patch("app.api.v1.routers.documents.chat.ChatService") as mock_chat,
        ):
            mock_embed.return_value.search_similar_chunks.return_value = []
            mock_chat.return_value.answer_question_with_chunks.return_value = {
                "answer": "This is a mock legal answer.",
                "citations": [],
                "confidence": "HIGH",
                "disclaimer": "This AI response assists document review and is not legal advice.",
            }

            responses = []
            for i in range(11):
                res = client.post(
                    f"/api/v1/documents/{TEST_DOC_ID}/chat",
                    json={"question": f"What is clause {i}?"},
                    headers={"Authorization": "Bearer mock-token"},
                )
                responses.append(res)

            # First 10 requests must succeed (HTTP 200)
            for i in range(10):
                assert responses[i].status_code == 200, (
                    f"Chat request {i+1} failed with status {responses[i].status_code}: {responses[i].text}"
                )

            # 11th request must be rate limited with HTTP 429
            assert responses[10].status_code == 429, (
                f"Expected 11th request to be 429, got {responses[10].status_code}: {responses[10].text}"
            )
            body = responses[10].json()
            assert "Rate limit exceeded" in body["error"]
            assert "Rate limit exceeded" in body["detail"]
    finally:
        app.dependency_overrides.clear()


def test_chat_endpoint_n8n_internal_token_exemption():
    """
    Ensure internal service calls carrying a valid X-Internal-Token (e.g. from n8n)
    bypass the chat rate limit and are not blocked even after 12+ rapid calls.
    """
    app.dependency_overrides[get_db] = override_get_db

    valid_token = settings.INTERNAL_SERVICE_TOKEN or "placeholder_internal_service_token_change_me"

    try:
        with (
            patch("app.api.v1.routers.documents.chat.EmbeddingService") as mock_embed,
            patch("app.api.v1.routers.documents.chat.ChatService") as mock_chat,
        ):
            mock_embed.return_value.search_similar_chunks.return_value = []
            mock_chat.return_value.answer_question_with_chunks.return_value = {
                "answer": "Internal service automated analysis answer.",
                "citations": [],
                "confidence": "HIGH",
                "disclaimer": "This AI response assists document review and is not legal advice.",
            }

            # Execute 12 rapid chat requests (more than the 10/min limit)
            for i in range(12):
                res = client.post(
                    f"/api/v1/documents/{TEST_DOC_ID}/chat",
                    json={"question": f"Automated question {i}?"},
                    headers={"X-Internal-Token": valid_token},
                )
                assert res.status_code == 200, (
                    f"Internal chat request {i+1} was unexpectedly throttled: status {res.status_code}, {res.text}"
                )
    finally:
        app.dependency_overrides.clear()


def test_rate_limit_per_ip_isolation():
    """
    Ensure rate limits are strictly isolated per IP address:
    Exceeding limit on IP A (5 requests) does not affect or throttle IP B.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    ip_a = "198.51.100.1"
    ip_b = "198.51.100.2"

    try:
        with (
            patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test.pdf"),
            patch("app.services.ocr_service.OCRService.process_document", return_value=("Mock contract text content", "native", 1.0)),
            patch("app.api.v1.routers.documents.trigger_n8n_webhook"),
        ):

            # IP A sends 5 requests (all 200)
            for i in range(5):
                res = client.post(
                    "/api/v1/documents",
                    files={"file": (f"ipa_{i}.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
                    headers={"Authorization": "Bearer mock-token", "X-Forwarded-For": ip_a},
                )
                assert res.status_code == 200

            # IP A sends 6th request -> 429
            res_a6 = client.post(
                "/api/v1/documents",
                files={"file": ("ipa_blocked.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
                headers={"Authorization": "Bearer mock-token", "X-Forwarded-For": ip_a},
            )
            assert res_a6.status_code == 429

            # IP B sends 1st request -> must succeed with 200 (isolated bucket)
            res_b1 = client.post(
                "/api/v1/documents",
                files={"file": ("ipb_allowed.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
                headers={"Authorization": "Bearer mock-token", "X-Forwarded-For": ip_b},
            )
            assert res_b1.status_code == 200, f"Expected 200 for IP B, got {res_b1.status_code}"
    finally:
        app.dependency_overrides.clear()


def test_invalid_internal_token_is_not_exempt():
    """Ensure requests with an invalid X-Internal-Token are not granted exemption."""
    res = client.post(
        "/api/v1/documents",
        files={"file": ("bad_token.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")},
        headers={"X-Internal-Token": "completely-invalid-token"},
    )
    # Auth layer will reject the invalid token with 401 Unauthorized
    assert res.status_code == 401
    assert "Invalid internal service token" in res.json()["detail"]


def test_trigger_n8n_webhook_not_rate_limited():
    """Ensure internal outbound trigger_n8n_webhook operates asynchronously without rate limiting."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        async def run_calls():
            for i in range(10):
                await trigger_n8n_webhook(f"doc-{i}", f"file_{i}.pdf", "user@example.com")

        # Triggering 10 rapid outbound calls must not raise RateLimitExceeded
        asyncio.run(run_calls())
        assert mock_post.call_count == 10

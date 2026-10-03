"""
Unit tests for sanitized HTTP 500 exception responses and traceback leak prevention.
Verifies SEC-ERR-001-EXCEPTION-SANITIZATION requirements.
"""

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models import Document, User

client = TestClient(app)
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def override_get_current_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="test@example.com", role="user")


def test_upload_document_sanitizes_500_error():
    """
    Ensure document upload unhandled exception does not leak traceback or sensitive error message.
    """
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("Database connection string error: postgresql://secret:password@internal-db:5432/db")

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("test.pdf", b"%PDF-1.4 mock content", "application/pdf")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail == "An internal error occurred while processing document upload. Please try again or contact support."
        assert "password" not in detail
        assert "internal-db" not in detail
        assert "RuntimeError" not in detail
    finally:
        app.dependency_overrides.clear()


def test_delete_document_sanitizes_500_error():
    """
    Ensure document deletion unhandled exception returns client-safe error message.
    """
    mock_db = MagicMock()
    fake_doc = Document(id=uuid.uuid4(), user_id=TEST_USER_ID, filename="contract.pdf", status="processed")
    mock_db.query.return_value.filter.return_value.first.return_value = fake_doc
    # Cause delete to fail with sensitive internal exception
    mock_db.delete.side_effect = Exception("psycopg2.OperationalError: server closed connection unexpectedly")

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.delete(
            f"/api/v1/documents/{fake_doc.id}",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail == "Unable to complete document deletion."
        assert "OperationalError" not in detail
        assert "psycopg2" not in detail
    finally:
        app.dependency_overrides.clear()


def test_analyze_contract_sanitizes_500_error():
    """
    Ensure document analysis failure returns client-safe generic error.
    """
    mock_db = MagicMock()
    fake_doc = Document(id=uuid.uuid4(), user_id=TEST_USER_ID, filename="contract.pdf", status="processed")
    fake_extracted = MagicMock()
    fake_extracted.content = "Sample contract text."

    def mock_query(model):
        m = MagicMock()
        if model == Document:
            m.filter.return_value.first.return_value = fake_doc
        else:
            m.filter.return_value.first.return_value = fake_extracted
        return m

    mock_db.query.side_effect = mock_query

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.routers.documents.LLMService") as mock_llm_cls:
        mock_llm_instance = mock_llm_cls.return_value
        mock_llm_instance.analyze_contract.side_effect = Exception("Anthropic API Key invalid: sk-ant-secret-key-12345")

        try:
            response = client.post(
                f"/api/v1/documents/{fake_doc.id}/analyze",
                headers={"Authorization": "Bearer mock-token"},
            )
            assert response.status_code == 500
            detail = response.json()["detail"]
            assert detail == "Document analysis pipeline failed. Please retry."
            assert "sk-ant" not in detail
            assert "Anthropic" not in detail
        finally:
            app.dependency_overrides.clear()

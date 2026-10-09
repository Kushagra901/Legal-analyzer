"""
Unit tests for strict file extension, MIME type, and magic-byte signature validation.
Verifies SEC-UPL-001-STRICT-FILE-VALIDATION requirements.
"""

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models import User

client = TestClient(app)
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def override_get_current_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="test@example.com", role="user")


def test_unsupported_file_extension_rejected():
    """
    Ensure files with unauthorized extensions are rejected even if MIME type is valid.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("malicious.exe", b"%PDF-1.4 mock content", "application/pdf")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "Unsupported file extension '.exe'" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_disallowed_mime_type_rejected():
    """
    Ensure files with prohibited MIME types are rejected even if extension is allowed.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("spoofed.pdf", b"%PDF-1.4 mock content", "application/x-msdownload")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "MIME type 'application/x-msdownload' is not permitted" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_pdf_magic_byte_mismatch_rejected():
    """
    Ensure files with .pdf extension but invalid magic bytes are rejected.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("corrupt.pdf", b"NOT_A_REAL_PDF_HEADER", "application/pdf")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "File content does not match the expected signature for a .pdf document." in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_docx_magic_byte_mismatch_rejected():
    """
    Ensure files with .docx extension but invalid zip header are rejected.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("corrupt.docx", b"NOT_A_ZIP_CONTAINER", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "File content does not match the expected signature for a .docx document." in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_png_magic_byte_mismatch_rejected():
    """
    Ensure files with .png extension but invalid PNG signature are rejected.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("fake.png", b"GIF89a corrupted image", "image/png")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "File content does not match the expected signature for a .png document." in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_valid_pdf_magic_bytes_accepted():
    """
    Ensure genuine PDF magic bytes pass validation and proceed through upload pipeline.
    """
    import datetime
    mock_db = MagicMock()

    def mock_add(entity):
        if hasattr(entity, "uploaded_at") and entity.uploaded_at is None:
            entity.uploaded_at = datetime.datetime.now(datetime.UTC)
        if hasattr(entity, "id") and entity.id is None:
            entity.id = uuid.uuid4()

    mock_db.add.side_effect = mock_add
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test.pdf"), \
         patch("app.services.ocr_service.OCRService.process_document", return_value=("Extracted text", "native", 1.0)), \
         patch("app.workers.tasks.execute_document_analysis"), \
         patch("app.api.v1.routers.documents.trigger_n8n_webhook"):
        try:
            response = client.post(
                "/api/v1/documents",
                files={"file": ("test.pdf", b"%PDF-1.7 genuine pdf bytes here", "application/pdf")},
                headers={"Authorization": "Bearer mock-token"},
            )
            assert response.status_code == 200
            assert response.json()["filename"] == "test.pdf"
            assert response.json()["status"] == "processing"
        finally:
            app.dependency_overrides.clear()


def test_streaming_upload_rejects_oversized_file():
    """
    Ensure streaming upload terminates immediately when accumulated chunk bytes exceed 10MB limit.
    """
    import io
    oversized_data = b"%PDF" + (b"0" * (10 * 1024 * 1024 + 64 * 1024))
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("oversized.pdf", io.BytesIO(oversized_data), "application/pdf")},
            headers={"Authorization": "Bearer mock-token"},
        )
        assert response.status_code == 400
        assert "File size exceeds maximum allowed limit of 10MB." in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# test_upload.py
"""
Unit Tests for Document Upload.
Tests file validations, database persistence, and audit logging.
"""
import io
import os
import sys
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import Base, get_db
from app.models import Document, AuditLog

# 1. Setup in-memory SQLite database for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in the temporary database
Base.metadata.create_all(bind=engine)

# 2. Dependency Override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Fixture to truncate database tables before every test."""
    db = TestingSessionLocal()
    # Clear tables
    db.query(AuditLog).delete()
    db.query(Document).delete()
    db.commit()
    db.close()

def test_upload_valid_pdf():
    """
    Test uploading a valid PDF document.
    """
    file_content = b"%PDF-1.4 mock PDF content"
    file_name = "test_contract.pdf"
    
    # Mock storage service to bypass Supabase network calls
    with patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test_contract.pdf") as mock_upload:
        response = client.post(
            "/api/v1/documents",
            files={"file": (file_name, io.BytesIO(file_content), "application/pdf")}
        )
        
        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == file_name
        assert data["status"] == "processing"
        assert "document_id" in data
        assert "storage_path" in data
        mock_upload.assert_called_once()

        # Verify DB entry
        db = TestingSessionLocal()
        doc = db.query(Document).filter(Document.filename == file_name).first()
        assert doc is not None
        assert doc.status == "processing"
        
        # Verify Audit Log entry
        audit = db.query(AuditLog).filter(AuditLog.document_id == doc.id).first()
        assert audit is not None
        assert "Document uploaded" in audit.action
        db.close()

def test_upload_invalid_file_type():
    """
    Test that uploading an unsupported file format (e.g. PNG) is rejected.
    """
    file_content = b"\x89PNG\r\n\x1a\n mock PNG content"
    file_name = "image.png"
    
    response = client.post(
        "/api/v1/documents",
        files={"file": (file_name, io.BytesIO(file_content), "image/png")}
    )
    
    # Verify rejection
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

    # Verify no DB records were created
    db = TestingSessionLocal()
    assert db.query(Document).count() == 0
    assert db.query(AuditLog).count() == 0
    db.close()

def test_upload_oversized_file():
    """
    Test that uploading a file larger than 10MB is rejected.
    """
    # 10.1 MB file content
    oversized_content = b"a" * (10 * 1024 * 1024 + 100 * 1024)
    file_name = "huge_contract.pdf"
    
    response = client.post(
        "/api/v1/documents",
        files={"file": (file_name, io.BytesIO(oversized_content), "application/pdf")}
    )
    
    # Verify rejection
    assert response.status_code == 400
    assert "exceeds maximum limit of 10MB" in response.json()["detail"]

    # Verify no DB records were created
    db = TestingSessionLocal()
    assert db.query(Document).count() == 0
    assert db.query(AuditLog).count() == 0
    db.close()

def test_list_documents():
    """
    Test retrieving the list of uploaded documents.
    """
    from datetime import datetime, timedelta, timezone
    db = TestingSessionLocal()
    # Use dummy user UUID
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    now = datetime.now(timezone.utc)
    doc1 = Document(filename="doc1.pdf", user_id=user_id, status="processing", uploaded_at=now - timedelta(minutes=5))
    doc2 = Document(filename="doc2.pdf", user_id=user_id, status="completed", uploaded_at=now)
    db.add(doc1)
    db.add(doc2)
    db.commit()
    db.close()
    
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Ensure they are sorted by uploaded_at desc
    assert data[0]["filename"] == "doc2.pdf"
    assert data[1]["filename"] == "doc1.pdf"

def test_ocr_service_decision():
    """
    Test the OCR fallback decision threshold in OCRService.
    """
    from app.services.ocr_service import OCRService
    service = OCRService()
    
    # 0 characters (scanned) should use OCR
    assert service.should_use_ocr("") is True
    # 150 characters (noisy metadata/scanned) should use OCR
    assert service.should_use_ocr("a" * 150) is True
    # 250 characters (legitimate text) should NOT use OCR
    assert service.should_use_ocr("a" * 250) is False



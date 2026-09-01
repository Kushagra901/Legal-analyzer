# test_upload.py
"""
Unit Tests for Document Upload.
Tests file validations, database persistence, and audit logging.
"""
import io
import json
import os
import sys
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    Clause,
    ComplianceCheck,
    Document,
    ExtractedText,
    LegalReference,
    Organization,
    RiskFlag,
    User,
)

# 1. Setup in-memory SQLite database for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in the temporary database
Base.metadata.create_all(bind=engine)

from datetime import UTC

from fastapi import Depends, Request

from app.core.auth import get_current_user


# 2. Dependency Override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user(request: Request, db: Session = Depends(override_get_db)):
    internal_token = request.headers.get("x-internal-token")
    if internal_token is not None:
        if internal_token != "placeholder_internal_service_token_change_me":
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid internal service token.")
        system_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        return User(
            id=system_uuid,
            org_id=system_uuid,
            email="system-internal@service.local",
            role="admin"
        )
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    org = db.query(Organization).filter(Organization.id == test_uuid).first()
    if not org:
        org = Organization(id=test_uuid, name="Test Org", plan="free")
        db.add(org)
        db.commit()
    user = db.query(User).filter(User.id == test_uuid).first()
    if not user:
        user = User(id=test_uuid, org_id=test_uuid, email="test@example.com", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Fixture to truncate database tables and set dependency overrides before every test."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    # Clear all tables to prevent cross-test data pollution
    db.query(AuditLog).delete()
    db.query(LegalReference).delete()
    db.query(ComplianceCheck).delete()
    db.query(RiskFlag).delete()
    db.query(Clause).delete()
    db.query(ExtractedText).delete()
    db.query(Document).delete()
    db.commit()
    db.close()

def test_upload_valid_pdf():
    """
    Test uploading a valid PDF document.
    """
    file_content = b"%PDF-1.4 mock PDF content"
    file_name = "test_contract.pdf"

    # Mock storage service, OCR text extraction, and n8n webhook trigger
    with patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test_contract.pdf") as mock_upload, \
         patch("app.services.ocr_service.OCRService.process_document", return_value=("This Mutual Non-Disclosure Agreement is governed by the laws of Delaware. Limitation of liability: neither party is liable for indirect damages. Either party may terminate with notice. Recipient will keep information confidential. Indemnity clause is included.", "native", 1.0)) as mock_ocr, \
         patch("app.api.v1.routers.documents.trigger_n8n_webhook") as mock_webhook:
        response = client.post(
            "/api/v1/documents",
            files={"file": (file_name, io.BytesIO(file_content), "application/pdf")},
            headers={"Authorization": "Bearer test-token"}
        )

        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == file_name
        assert data["status"] == "processing"
        assert "document_id" in data
        assert "storage_path" in data
        mock_upload.assert_called_once()
        mock_ocr.assert_called_once()
        mock_webhook.assert_called_once_with(data["document_id"], file_name, "test@example.com")

        # Execute background analysis task synchronously for test DB verification
        with patch("app.workers.tasks.SessionLocal", TestingSessionLocal):
            from app.workers.tasks import execute_document_analysis
            execute_document_analysis(data["document_id"])

        # Verify DB entry
        db = TestingSessionLocal()
        doc = db.query(Document).filter(Document.filename == file_name).first()
        assert doc is not None
        assert doc.status == "completed"
        assert doc.summary is not None
        assert doc.safety_score is not None
        assert doc.risk_level is not None

        # Verify Analysis Details DB entry
        clauses = db.query(Clause).filter(Clause.document_id == doc.id).all()
        assert len(clauses) > 0

        compliance = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).first()
        assert compliance is not None

        references = db.query(LegalReference).filter(LegalReference.document_id == doc.id).all()
        assert len(references) > 0

        # Verify Audit Log entry
        audit = db.query(AuditLog).filter(AuditLog.document_id == doc.id).first()
        assert audit is not None
        db.close()

def test_upload_valid_docx():
    """
    Test uploading a valid DOCX document.
    """
    from app.models import ExtractedText
    file_content = b"mock DOCX file content"
    file_name = "test_contract.docx"

    # Mock storage, OCR (returning DOCX parsed equivalent), and n8n webhook
    with patch("app.services.storage_service.StorageService.upload_file", return_value="documents/mock-uuid/test_contract.docx") as mock_upload, \
         patch("app.services.ocr_service.OCRService.process_document", return_value=("This Mutual Non-Disclosure Agreement is governed by the laws of Delaware. Limitation of liability: neither party is liable for indirect damages. Either party may terminate with notice. Recipient will keep information confidential.", "native", 1.0)) as mock_ocr, \
         patch("app.api.v1.routers.documents.trigger_n8n_webhook") as mock_webhook:
        response = client.post(
            "/api/v1/documents",
            files={"file": (file_name, io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers={"Authorization": "Bearer test-token"}
        )

        # Verify API response
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == file_name
        assert data["status"] == "processing"
        assert "document_id" in data
        assert "storage_path" in data
        mock_upload.assert_called_once()
        mock_ocr.assert_called_once()
        mock_webhook.assert_called_once_with(data["document_id"], file_name, "test@example.com")

        # Execute background analysis task synchronously for test DB verification
        with patch("app.workers.tasks.SessionLocal", TestingSessionLocal):
            from app.workers.tasks import execute_document_analysis
            execute_document_analysis(data["document_id"])

        # Verify DB entry
        db = TestingSessionLocal()
        doc = db.query(Document).filter(Document.filename == file_name).first()
        assert doc is not None
        assert doc.status == "completed"

        # Verify ExtractedText entry has parsing_confidence
        extracted = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
        assert extracted is not None
        assert extracted.parsing_confidence == 1.0
        db.close()

def test_upload_invalid_file_type():
    """
    Test that uploading an unsupported file format (e.g. GIF) is rejected.
    """
    file_content = b"GIF89a mock GIF content"
    file_name = "image.gif"

    response = client.post(
        "/api/v1/documents",
        files={"file": (file_name, io.BytesIO(file_content), "image/gif")},
        headers={"Authorization": "Bearer test-token"}
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
        files={"file": (file_name, io.BytesIO(oversized_content), "application/pdf")},
        headers={"Authorization": "Bearer test-token"}
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
    from datetime import datetime, timedelta
    db = TestingSessionLocal()
    # Use dummy user UUID
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    now = datetime.now(UTC)
    doc1 = Document(filename="doc1.pdf", user_id=user_id, status="processing", uploaded_at=now - timedelta(minutes=5))
    doc2 = Document(filename="doc2.pdf", user_id=user_id, status="completed", uploaded_at=now)
    db.add(doc1)
    db.add(doc2)
    db.commit()
    db.close()

    response = client.get("/api/v1/documents", headers={"Authorization": "Bearer test-token"})
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


def test_get_document():
    """
    Test retrieving document details and dynamic analysis from database.
    """
    from app.models import ExtractedText
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    # Create Document
    doc = Document(
        id=uuid.uuid4(),
        filename="governing_law_test.pdf",
        user_id=user_id,
        status="completed",
        summary="A test contract summary.",
        safety_score=85,
        risk_level="LOW"
    )
    db.add(doc)
    db.flush()

    # Create ExtractedText
    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="This Agreement is governed by the laws of California.",
        method="native"
    )
    db.add(extracted)

    # Create Clause
    clause = Clause(
        id=uuid.uuid4(),
        document_id=doc.id,
        clause_type="Governing Law & Jurisdiction",
        clause_text="This Agreement is governed by the laws of California."
    )
    db.add(clause)
    db.flush()

    # Create RiskFlag
    flag = RiskFlag(
        id=uuid.uuid4(),
        clause_id=clause.id,
        severity="LOW",
        explanation="Standard governing law."
    )
    db.add(flag)

    # Create ComplianceCheck
    compliance = ComplianceCheck(
        id=uuid.uuid4(),
        document_id=doc.id,
        rule_set="standard_nda",
        result=json.dumps([])
    )
    db.add(compliance)

    # Create LegalReference
    ref = LegalReference(
        id=uuid.uuid4(),
        document_id=doc.id,
        source="California Civil Code Section 1646",
        citation="Governs law selection."
    )
    db.add(ref)
    doc_id = str(doc.id)
    db.commit()
    db.close()

    # Fetch document details
    response = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["filename"] == "governing_law_test.pdf"
    assert data["status"] == "completed"
    assert data["analysis"]["safety_score"] == 85
    assert len(data["analysis"]["clauses"]) == 1
    assert data["analysis"]["clauses"][0]["type"] == "Governing Law & Jurisdiction"
    assert len(data["analysis"]["citations"]) == 1
    assert data["analysis"]["citations"][0]["source"] == "California Civil Code Section 1646"


def test_get_report():
    """
    Test retrieving a report.
    """
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    # Create Document
    doc = Document(
        id=uuid.uuid4(),
        filename="report_test.pdf",
        user_id=user_id,
        status="completed",
        summary="A test contract summary for report.",
        safety_score=75,
        risk_level="MEDIUM"
    )
    db.add(doc)
    db.flush()

    # Create LegalReference
    ref = LegalReference(
        id=uuid.uuid4(),
        document_id=doc.id,
        source="Delaware General Corporation Law",
        citation="Section 102."
    )
    db.add(ref)
    doc_id = str(doc.id)
    db.commit()
    db.close()

    response = client.get(f"/api/v1/reports/{doc_id}", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["safety_score"] == 75
    assert data["risk_level"] == "MEDIUM"
    assert len(data["citations"]) == 1
    assert data["citations"][0]["source"] == "Delaware General Corporation Law"


def test_get_document_via_internal_token():
    """
    Test retrieving a document via the internal service bypass token.
    """
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc = Document(
        id=uuid.uuid4(),
        filename="internal_auth_test.pdf",
        user_id=user_id,
        status="completed"
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)
    db.close()

    response = client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"x-internal-token": "placeholder_internal_service_token_change_me"}
    )
    assert response.status_code == 200
    assert response.json()["document_id"] == doc_id


def test_get_document_via_invalid_internal_token():
    """
    Test that retrieving a document with an invalid X-Internal-Token fails.
    """
    response = client.get(
        "/api/v1/documents/00000000-0000-0000-0000-000000000000",
        headers={"x-internal-token": "wrong-token"}
    )
    assert response.status_code == 401
    assert "Invalid internal service token" in response.json()["detail"]


def test_get_report_via_internal_token():
    """
    Test retrieving a report via the internal service bypass token.
    """
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc = Document(
        id=uuid.uuid4(),
        filename="internal_report_test.pdf",
        user_id=user_id,
        status="completed",
        summary="Internal report test summary."
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)
    db.close()

    response = client.get(
        f"/api/v1/reports/{doc_id}",
        headers={"x-internal-token": "placeholder_internal_service_token_change_me"}
    )
    assert response.status_code == 200
    assert response.json()["document_id"] == doc_id





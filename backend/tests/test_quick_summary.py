"""
Unit and integration tests for POST /api/v1/documents/{document_id}/quick-summary.
Validates immediate fast overview generation, persistence, audit logging, and tenant isolation.
"""
import uuid
from unittest.mock import patch

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.database_models import (
    AuditLog,
    ChatMessage,
    Clause,
    Document,
    DocumentChunk,
    ExtractedText,
    Organization,
    User,
)
from app.services.llm_service import LLMService

# SQLite in-memory setup for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
current_user_override = {"user_id": TEST_USER_ID}


def override_get_current_user(request: Request, db=Depends(override_get_db)):
    uid = current_user_override["user_id"]
    org = db.query(Organization).filter(Organization.id == uid).first()
    if not org:
        org = Organization(id=uid, name="Test Org", plan="free")
        db.add(org)
        db.commit()
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        user = User(id=uid, org_id=uid, email=f"user_{uid.hex[:8]}@example.com", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    current_user_override["user_id"] = TEST_USER_ID

    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.query(ChatMessage).delete()
    db.query(DocumentChunk).delete()
    db.query(ExtractedText).delete()
    db.query(Clause).delete()
    db.query(Document).delete()
    db.commit()
    db.close()
    yield


def test_quick_summary_service_rule_fallback():
    """Test LLMService quick summary generates deterministic structured output on fallback."""
    service = LLMService()
    text = """
    MUTUAL NON-DISCLOSURE AGREEMENT
    This Agreement is entered into between Alpha Corp and Beta LLC.
    Confidential Information shall be protected for 2 years.
    Governing law is California.
    """
    result = service.generate_quick_summary(text, "mutual_nda.pdf")
    assert "quick_summary" in result
    assert "Non-Disclosure" in result["document_type"] or "Agreement" in result["document_type"]
    assert isinstance(result["key_points"], list)
    assert len(result["key_points"]) > 0
    assert result["estimated_risk_level"] in ["LOW", "MEDIUM", "HIGH", "NEUTRAL"]
    assert "disclaimer" in result


def test_quick_summary_success():
    """
    Test that POST /api/v1/documents/{document_id}/quick-summary returns 200 with structured 2-3 sentence overview.
    """
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=TEST_USER_ID,
        filename="sample_mutual_nda.pdf",
        status="uploaded"
    )
    db.add(doc)
    db.commit()

    text_obj = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="""MUTUAL NON-DISCLOSURE AGREEMENT
This Mutual Non-Disclosure Agreement is made and entered into as of January 15, 2026, by and between Alpha Corp and Beta LLC.
1. Confidential Information: Both parties agree to protect proprietary information disclosed during commercial evaluations.
2. Term: The confidentiality obligations shall survive for a period of 2 years from disclosure.
3. Governing Law: This Agreement shall be governed by the laws of California.
""",
        method="native",
        parsing_confidence=1.0
    )
    db.add(text_obj)
    db.commit()
    db.close()

    response = client.post(f"/api/v1/documents/{doc_id}/quick-summary")
    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == str(doc_id)
    assert data["filename"] == "sample_mutual_nda.pdf"
    assert len(data["quick_summary"]) > 20
    assert "Non-Disclosure" in data["document_type"] or "Agreement" in data["document_type"]
    assert isinstance(data["key_points"], list)
    assert len(data["key_points"]) > 0
    assert data["estimated_risk_level"] in ["LOW", "MEDIUM", "HIGH", "NEUTRAL"]
    assert "legal advice" in data["disclaimer"].lower()

    # Verify document overview persisted in DB
    verify_db = TestingSessionLocal()
    updated_doc = verify_db.query(Document).filter(Document.id == doc_id).first()
    assert updated_doc.document_overview is not None
    assert len(updated_doc.document_overview) > 0

    # Verify audit log recorded
    logs = verify_db.query(AuditLog).filter(AuditLog.document_id == doc_id).all()
    assert any("Quick summary" in log.action for log in logs)
    verify_db.close()


def test_quick_summary_tenant_isolation():
    """
    Ensure users from other organizations cannot access or trigger quick summary.
    """
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=TEST_USER_ID,
        filename="confidential_contract.pdf",
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.close()

    # Switch to another user in different organization
    other_user_id = uuid.uuid4()
    current_user_override["user_id"] = other_user_id

    response = client.post(f"/api/v1/documents/{doc_id}/quick-summary")
    assert response.status_code in [403, 404]


def test_quick_summary_non_existent_document():
    """
    Ensure calling non-existent document ID returns 404.
    """
    fake_id = str(uuid.uuid4())
    response = client.post(f"/api/v1/documents/{fake_id}/quick-summary")
    assert response.status_code == 404

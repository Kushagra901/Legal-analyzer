# test_deep_extraction.py
"""
Unit and integration tests for Deep Extraction Service and Endpoint.
Tests prompt structure, fallback tiers, schema validation, and database caching.
"""
import os
import sys
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, Request

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    DeepExtraction,
    Document,
    ExtractedText,
    Organization,
    User,
)
from app.services.deep_extraction_service import DeepExtractionService

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


def override_get_current_user(request: Request, db=Depends(override_get_db)):
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
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.query(DeepExtraction).delete()
    db.query(ExtractedText).delete()
    db.query(Document).delete()
    db.commit()
    db.close()
    yield


# --- Unit Tests for DeepExtractionService ---

MOCK_DEEP_EXTRACTION_SUCCESS = {
    "deal_terms": {
        "parties": ["Acme Corp", "Beta LLC"],
        "effective_date": "2026-01-01",
        "expiration_date": "2027-01-01",
        "auto_renewal": True,
        "renewal_notice_days": 60,
        "governing_law": "Delaware",
        "jurisdiction": "Delaware Chancery Court",
        "document_type": "Master Services Agreement"
    },
    "obligations": [
        {
            "party": "Acme Corp",
            "obligation": "Provide monthly SLA reports",
            "deadline": "5th of each month",
            "trigger": "Monthly billing cycle",
            "penalty": "Service credit"
        }
    ],
    "risk_flags": [
        {
            "clause_type": "Indemnification",
            "severity": "HIGH",
            "issue": "Uncapped indemnification obligation",
            "original_text": "Vendor agrees to unconditionally indemnify...",
            "page_reference": "Section 9.1"
        }
    ],
    "missing_protections": [
        "No bilateral confidentiality clause",
        "No force majeure provision"
    ],
    "redline_suggestions": [
        {
            "clause_type": "Indemnification",
            "original_text": "Vendor agrees to unconditionally indemnify...",
            "suggested_replacement": "Each party shall indemnify the other up to the liability cap...",
            "rationale": "Aligns indemnity with overall contract liability limit."
        }
    ],
    "executive_summary": "Standard MSA with unbalanced indemnification risk.",
    "confidence": "HIGH"
}


def test_deep_extraction_service_gemini_success():
    """Test that DeepExtractionService parses valid LLM response."""
    service = DeepExtractionService()

    with patch.object(service.llm_service, "_call_gemini", return_value=MOCK_DEEP_EXTRACTION_SUCCESS):
        with patch.object(service.llm_service, "gemini_api_key", "mock_key"):
            result = service.extract_deep("Sample contract text between Acme Corp and Beta LLC.")
            assert result["confidence"] == "HIGH"
            assert len(result["deal_terms"]["parties"]) == 2
            assert result["deal_terms"]["auto_renewal"] is True
            assert len(result["obligations"]) == 1
            assert len(result["risk_flags"]) == 1
            assert len(result["redline_suggestions"]) == 1


def test_deep_extraction_service_rule_based_fallback():
    """Test offline rule-based fallback when LLMs fail."""
    service = DeepExtractionService()

    with patch.object(service.llm_service, "anthropic_api_key", None):
        with patch.object(service.llm_service, "gemini_api_key", None):
            with patch.object(service.llm_service, "api_key", None):
                sample_text = "This agreement is governed by the laws of Delaware. Effective date: January 1, 2026."
                result = service.extract_deep(sample_text)
                assert result["confidence"] == "LOW"
                assert "governing_law" in result["deal_terms"]
                assert "Delaware" in result["deal_terms"]["governing_law"]
                assert "effective_date" in result["deal_terms"]


def test_deep_extraction_endpoint():
    """Test POST /api/v1/documents/{id}/deep-extract endpoint."""
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename="contract_test.pdf",
        status="completed"
    )
    db.add(doc)
    db.commit()

    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Master Agreement. Governing law: State of New York. Effective date: March 1, 2026.",
        method="native_pdf",
        parsing_confidence=0.95
    )
    db.add(extracted)
    db.commit()
    db.close()

    with patch.object(DeepExtractionService, "extract_deep", return_value=MOCK_DEEP_EXTRACTION_SUCCESS):
        res = client.post(f"/api/v1/documents/{doc_id}/deep-extract")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == str(doc_id)
        assert data["deal_terms"]["auto_renewal"] is True
        assert len(data["risk_flags"]) == 1
        assert len(data["redline_suggestions"]) == 1

        # Test idempotency: Second call re-extracts and updates the existing record without duplicate key error
        updated_mock = dict(MOCK_DEEP_EXTRACTION_SUCCESS)
        updated_mock["executive_summary"] = "Updated executive summary prose."
        with patch.object(DeepExtractionService, "extract_deep", return_value=updated_mock):
            second_res = client.post(f"/api/v1/documents/{doc_id}/deep-extract")
            assert second_res.status_code == 200
            assert second_res.json()["document_id"] == str(doc_id)
            assert second_res.json()["executive_summary"] == "Updated executive summary prose."

        # Verify exactly one row exists in the database for doc_id
        verify_db = TestingSessionLocal()
        total_records = verify_db.query(DeepExtraction).filter(DeepExtraction.document_id == doc_id).count()
        verify_db.close()
        assert total_records == 1

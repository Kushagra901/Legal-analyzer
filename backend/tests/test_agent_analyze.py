"""
test_agent_analyze.py
Unit and integration tests for:
1. Ollama first-tier check in LLMService.analyze_contract().
2. POST /api/v1/documents/{document_id}/agent-analyze 5-agent pipeline.
3. Downstream compatibility (persistence to clauses, risk_flags, documents columns).
"""

import os
import sys
import uuid
from unittest.mock import patch

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    Clause,
    ComplianceCheck,
    Document,
    ExtractedText,
    Organization,
    Report,
    RiskFlag,
    User,
)
from app.services.llm_service import LLMService
from app.services.ollama_service import OllamaService

# Setup in-memory SQLite database
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


def override_get_current_user(request: Request, db: Session = Depends(override_get_db)):
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
    return user


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Clear database tables and ensure default test user before each test."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.query(RiskFlag).delete()
    db.query(Clause).delete()
    db.query(ExtractedText).delete()
    db.query(Report).delete()
    db.query(ComplianceCheck).delete()
    db.query(Document).delete()

    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    org = db.query(Organization).filter(Organization.id == test_uuid).first()
    if not org:
        org = Organization(id=test_uuid, name="Test Org", plan="free")
        db.add(org)
    user = db.query(User).filter(User.id == test_uuid).first()
    if not user:
        user = User(id=test_uuid, org_id=test_uuid, email="test@example.com", role="user")
        db.add(user)
    db.commit()
    db.close()
    yield
    app.dependency_overrides.clear()


# =============================================================================
# 1. Tests for Ollama Tier in LLMService.analyze_contract()
# =============================================================================

def test_analyze_contract_ollama_tier_success():
    """
    Verify that when Ollama is healthy and returns valid schema,
    analyze_contract returns Ollama's result as the first tier.
    """
    mock_ollama_data = {
        "summary": "Ollama analyzed agreement.",
        "document_overview": "Mutual non-disclosure contract.",
        "plain_english_summary": "Both parties protect proprietary data.",
        "parties": ["Alpha Inc", "Beta LLC"],
        "key_dates": {
            "effective_date": "2025-01-01",
            "expiration_date": "2027-01-01"
        },
        "missing_sections": ["Dispute Resolution"],
        "safety_score": 88,
        "risk_level": "LOW",
        "clauses": [
            {
                "clause_type": "Confidentiality Obligations",
                "clause_text": "Recipient shall maintain secrecy.",
                "severity": "LOW",
                "explanation": "Standard confidentiality terms.",
                "category": "Confidentiality & IP",
                "confidence_score": 0.95
            }
        ],
        "citations": [
            {"source": "Restatement of Contracts", "citation": "Section 71"}
        ],
        "recommendations": ["Ensure mutual return of data."]
    }

    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "_generate_json_with_retry", return_value=mock_ollama_data):
        service = LLMService()
        result = service.analyze_contract("Sample contract text between Alpha Inc and Beta LLC.")
        assert result["summary"] == "Ollama analyzed agreement."
        assert result["safety_score"] == 88
        assert result["risk_level"] == "LOW"
        assert len(result["clauses"]) == 1
        assert result["parties"] == ["Alpha Inc", "Beta LLC"]


def test_analyze_contract_ollama_tier_failure_falls_back():
    """
    Verify that if Ollama is healthy but returns invalid schema or fails,
    it logs an error and falls back to Gemini or Rule-based.
    """
    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "_generate_json_with_retry", side_effect=ValueError("Invalid JSON")), \
         patch.object(LLMService, "_call_gemini", side_effect=RuntimeError("Gemini down")):
        service = LLMService()
        result = service.analyze_contract("Sample contract with confidential terms.")
        # Falls back to rule-based fallback
        assert "Offline rule-based fallback" in result["summary"]
        assert len(result["clauses"]) > 0


def test_analyze_contract_ollama_unhealthy_skips_ollama():
    """
    Verify that when Ollama is unhealthy/unconfigured, it is skipped entirely
    without calling generate_json.
    """
    with patch.object(OllamaService, "check_health", return_value=False), \
         patch.object(OllamaService, "_generate_json_with_retry") as mock_ollama_gen, \
         patch.object(LLMService, "_call_gemini", side_effect=RuntimeError("Gemini down")):
        service = LLMService()
        result = service.analyze_contract("Sample agreement.")
        mock_ollama_gen.assert_not_called()
        assert "Offline rule-based fallback" in result["summary"]


def test_get_ollama_status_healthy():
    """Verify /api/v1/system/ollama-status returns healthy=True when Ollama is reachable."""
    with patch.object(OllamaService, "check_health", return_value=True):
        resp = client.get("/api/v1/system/ollama-status?document_id=doc-12345")
        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is True
        assert data["document_id"] == "doc-12345"
        assert "base_url" in data
        assert "model" in data


def test_get_ollama_status_unhealthy():
    """Verify /api/v1/system/ollama-status returns healthy=False when Ollama is unreachable."""
    with patch.object(OllamaService, "check_health", return_value=False):
        resp = client.get("/api/v1/system/ollama-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is False
        assert data["document_id"] is None


# =============================================================================
# 2. Tests for POST /api/v1/documents/{document_id}/agent-analyze
# =============================================================================

def test_agent_analyze_pipeline_execution():
    """
    Verify the 5-agent pipeline executes in order and writes to clauses,
    risk_flags, and documents table columns.
    """
    db = TestingSessionLocal()
    test_user = db.query(User).first()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=test_user.id,
        filename="vendor_agreement.pdf",
        status="processing"
    )
    db.add(doc)

    sample_contract_text = (
        "Article 1. Scope of Work\n"
        "Vendor shall provide IT consultancy services.\n\n"
        "Section 2. Indemnification Obligations\n"
        "Vendor agrees to indemnify customer for all damages with unlimited liability.\n\n"
        "Section 3. Governing Law\n"
        "This agreement shall be governed by the laws of Delaware."
    )
    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=sample_contract_text,
        method="native_pdf",
        parsing_confidence=1.0
    )
    db.add(ext)
    db.commit()
    db.close()

    response = client.post(f"/api/v1/documents/{doc_id}/agent-analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "analyzed"
    assert data["document_id"] == str(doc_id)
    assert data["safety_score"] is not None
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert data["summary"] is not None

    # Verify database persistence
    db = TestingSessionLocal()
    updated_doc = db.query(Document).filter(Document.id == doc_id).first()
    assert updated_doc.status == "analyzed"
    assert updated_doc.summary != ""
    assert updated_doc.safety_score is not None
    assert updated_doc.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(updated_doc.parties, list)
    assert isinstance(updated_doc.key_dates, dict)

    # Verify clauses and risk flags created
    db_clauses = db.query(Clause).filter(Clause.document_id == doc_id).all()
    assert len(db_clauses) >= 2

    # Verify unlimited indemnity triggered a RiskFlag
    flags = db.query(RiskFlag).join(Clause).filter(Clause.document_id == doc_id).all()
    assert len(flags) >= 1
    assert any(f.severity in ("MEDIUM", "HIGH") for f in flags)

    # Verify audit log entry written
    audit = db.query(AuditLog).filter(AuditLog.document_id == doc_id).first()
    assert audit is not None
    assert "5-agent pipeline completed" in audit.action
    db.close()


def test_agent_analyze_with_mocked_ollama():
    """
    Verify all 5 Ollama master prompt methods are invoked when Ollama is healthy.
    """
    db = TestingSessionLocal()
    test_user = db.query(User).first()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=test_user.id,
        filename="master_service_agreement.pdf",
        status="processing"
    )
    db.add(doc)

    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Article 1. Scope\nWork description.\n\nSection 2. Payment\nNet 30 days.",
        method="native_pdf",
        parsing_confidence=1.0
    )
    db.add(ext)
    db.commit()
    db.close()

    mock_classification = {
        "document_type": "Master Services Agreement",
        "confidence": 0.94,
        "summary_category": "Commercial",
        "key_indicators": ["Services", "Payment"]
    }
    mock_entities = {
        "parties": ["Client Corp", "Provider Inc"],
        "effective_date": "2025-06-01",
        "expiration_date": "2026-06-01",
        "auto_renewal": True,
        "renewal_notice_days": 30,
        "governing_law": "California",
        "jurisdiction": "San Francisco",
        "document_type": "Master Services Agreement",
        "key_amounts": ["$10,000/mo"]
    }
    mock_risk = {
        "type": "Commercial Terms",
        "severity": "LOW",
        "explanation": "Standard payment terms.",
        "issue": "",
        "recommendation": "Acceptable.",
        "confidence_score": 0.92
    }
    mock_comp = {
        "status": "compliant",
        "rule_set": "Master Services Agreement",
        "violations": [],
        "missing_clauses": ["Audit Rights"],
        "safety_score": 90,
        "risk_level": "LOW"
    }
    mock_summary = "Executive Brief: Provider Inc agrees to deliver commercial services to Client Corp."

    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "classify_document", return_value=mock_classification) as mock_classify, \
         patch.object(OllamaService, "extract_entities", return_value=mock_entities) as mock_extract, \
         patch.object(OllamaService, "analyze_clause_risk", return_value=mock_risk) as mock_risk_call, \
         patch.object(OllamaService, "audit_compliance", return_value=mock_comp) as mock_comp_call, \
         patch.object(OllamaService, "generate_summary", return_value=mock_summary) as mock_sum_call:

        response = client.post(f"/api/v1/documents/{doc_id}/agent-analyze")
        assert response.status_code == 200

        # Assert all 5 master methods were called in pipeline sequence
        mock_classify.assert_called_once()
        mock_extract.assert_called_once()
        assert mock_risk_call.call_count >= 2
        assert mock_comp_call.call_count >= 2
        mock_sum_call.assert_called_once()

        data = response.json()
        assert data["status"] == "analyzed"
        assert "Provider Inc" in data["summary"]


def test_agent_analyze_non_existent_document_404():
    """Verify that calling agent-analyze with an invalid document UUID returns 404."""
    random_id = uuid.uuid4()
    response = client.post(f"/api/v1/documents/{random_id}/agent-analyze")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_agent_analyze_downstream_compatibility():
    """
    Verify that after running agent-analyze, downstream endpoints
    (GET /documents/{id} and report generation) work identically.
    """
    db = TestingSessionLocal()
    test_user = db.query(User).first()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=test_user.id,
        filename="test_nda.pdf",
        status="processing"
    )
    db.add(doc)

    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="Article 1. Confidential Information\nProprietary data.\n\nSection 2. Term\nTwo years.",
        method="native_pdf",
        parsing_confidence=1.0
    )
    db.add(ext)
    db.commit()
    db.close()

    # 1. Run agent analysis
    analyze_resp = client.post(f"/api/v1/documents/{doc_id}/agent-analyze")
    assert analyze_resp.status_code == 200

    # 2. Query document details (GET /documents/{doc_id})
    doc_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert doc_resp.status_code == 200
    doc_data = doc_resp.json()
    assert doc_data["status"] == "analyzed"
    assert doc_data["analysis"] is not None
    assert doc_data["analysis"]["safety_score"] is not None
    assert len(doc_data["analysis"]["clauses"]) >= 2

    # 3. Trigger report export (POST /reports/{doc_id}/export?format=pdf)
    with patch("app.services.storage_service.StorageService.upload_file", return_value="mock_report_path.pdf"):
        export_resp = client.post(f"/api/v1/reports/{doc_id}/export?format=pdf")
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["document_id"] == str(doc_id)
        assert export_data["safety_score"] is not None
        assert len(export_data["clauses"]) >= 2

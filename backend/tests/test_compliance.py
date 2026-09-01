# test_compliance.py
"""
Unit Tests for the Compliance Checks module.
Tests the ComplianceService and LLMService compliance audit paths using the sample NDA PDF and mock data.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import httpx

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.compliance_service import ComplianceService
from app.services.ocr_service import OCRService

# --- Sample NDA Tests ---

def test_compliance_sample_nda_file():
    """
    Test compliance checks on the actual sample NDA PDF file.
    Verifies that native text is extracted and successfully audited.
    """
    ocr_service = OCRService()
    compliance_service = ComplianceService()

    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "test-documents", "sample-nda-test-document.pdf")

    assert os.path.exists(pdf_path), f"Sample NDA file not found at {pdf_path}"

    # Process document
    text, method, confidence = ocr_service.process_document(pdf_path)
    assert method == "native"
    assert len(text) > 0

    # Run compliance check in fallback/offline mode (default when GEMINI_API_KEY is not set)
    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["rule_set"] == "standard_nda"
        # The sample NDA has governing law, confidentiality scope, and a term length,
        # but it contains an indemnification provision which triggers a violation.
        assert result["status"] == "non-compliant"
        assert len(result["violations"]) == 1
        assert "Indemnification Provision Detected" in result["violations"][0]


def test_compliance_sample_docx_file():
    """
    Test compliance checks on the new sample DOCX contract document.
    """
    ocr_service = OCRService()
    compliance_service = ComplianceService()

    docx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "test-documents", "sample-contract.docx")

    assert os.path.exists(docx_path), f"Sample DOCX file not found at {docx_path}"

    # Process document
    text, method, confidence = ocr_service.process_document(docx_path)
    assert method == "native"
    assert confidence == 1.0
    assert len(text) > 0

    # Run compliance check in fallback/offline mode
    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["rule_set"] == "standard_nda"
        # Since it contains confidential, term (3 years), and governing law (New York),
        # and has no indemnification clauses, it should be fully compliant!
        assert result["status"] == "compliant"
        assert len(result["violations"]) == 0


# --- Rule-Based Local Fallback Tests ---

def test_compliance_local_fallback_all_compliant():
    """
    Test local fallback compliance checks where everything is compliant and standard.
    """
    compliance_service = ComplianceService()

    text = (
        "Mutual Non-Disclosure Agreement.\n"
        "1. Confidential Information definition: Recipient agrees to protect Disclosing Party's Confidential Information.\n"
        "2. Term: This Agreement is for a period of 5 years.\n"
        "3. Governing Law: This Agreement is governed by the laws of New York and the courts of New York City."
    )

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["status"] == "compliant"
        assert len(result["violations"]) == 0


def test_compliance_local_fallback_missing_confidentiality():
    """
    Test local fallback compliance flags missing confidentiality obligations.
    """
    compliance_service = ComplianceService()

    # Missing confidential/disclosure keywords
    text = (
        "General Consulting Agreement.\n"
        "Term: The agreement remains active for 2 years.\n"
        "Governing Law: Governed by the laws of California."
    )

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["status"] == "non-compliant"
        assert any("Missing Confidentiality Obligations" in v for v in result["violations"])


def test_compliance_local_fallback_missing_term():
    """
    Test local fallback compliance flags missing confidentiality term.
    """
    compliance_service = ComplianceService()

    # Missing term keywords
    text = (
        "Mutual Non-Disclosure Agreement.\n"
        "Confidential Information definition: Recipient agrees to protect Disclosing Party's Confidential Information.\n"
        "Governing Law: Governed by the laws of California."
    )

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["status"] == "non-compliant"
        assert any("Missing Confidentiality Term" in v for v in result["violations"])


def test_compliance_local_fallback_missing_governing_law():
    """
    Test local fallback compliance flags missing governing law/jurisdiction.
    """
    compliance_service = ComplianceService()

    # Missing governing law keywords
    text = (
        "Mutual Non-Disclosure Agreement.\n"
        "Confidential Information definition: Recipient agrees to protect Disclosing Party's Confidential Information.\n"
        "Term: The obligations survive for three years from the date of disclosure."
    )

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", ""):
        result = compliance_service.check_compliance(text, "standard_nda")

        assert result["status"] == "non-compliant"
        assert any("Missing Governing Law or Jurisdiction" in v for v in result["violations"])


# --- LLM-Based Online Compliance Audit Tests ---

MOCK_COMPLIANCE_SUCCESS_JSON = json.dumps({
    "violations": []
})

MOCK_COMPLIANCE_VIOLATIONS_JSON = json.dumps({
    "violations": [
        "Confidentiality Scope: The definition of confidential information is too narrow.",
        "Term Length: No termination term specified."
    ]
})

MOCK_GEMINI_RESPONSE_SUCCESS = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": MOCK_COMPLIANCE_SUCCESS_JSON
                    }
                ]
            }
        }
    ]
}

MOCK_GEMINI_RESPONSE_VIOLATIONS = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": MOCK_COMPLIANCE_VIOLATIONS_JSON
                    }
                ]
            }
        }
    ]
}


def test_compliance_llm_audit_success():
    """
    Test that ComplianceService successfully calls LLMService and returns no violations.
    """
    compliance_service = ComplianceService()

    # Set a mock API key to activate the LLM path
    with patch("app.services.llm_service.settings.GEMINI_API_KEY", "test-gemini-key"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_GEMINI_RESPONSE_SUCCESS
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client.post", return_value=mock_response):
            result = compliance_service.check_compliance("Some NDA contract content", "standard_nda")

            assert result["status"] == "compliant"
            assert len(result["violations"]) == 0


def test_compliance_llm_audit_violations():
    """
    Test that ComplianceService returns LLM-flagged violations when they are detected by Gemini.
    """
    compliance_service = ComplianceService()

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", "test-gemini-key"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_GEMINI_RESPONSE_VIOLATIONS
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client.post", return_value=mock_response):
            result = compliance_service.check_compliance("Some NDA contract content", "standard_nda")

            assert result["status"] == "non-compliant"
            assert len(result["violations"]) == 2
            assert "Confidentiality Scope" in result["violations"][0]
            assert "Term Length" in result["violations"][1]


def test_compliance_llm_audit_failure_fallback():
    """
    Test that ComplianceService falls back to local rule-based checking if Gemini API fails.
    """
    compliance_service = ComplianceService()

    with patch("app.services.llm_service.settings.GEMINI_API_KEY", "test-gemini-key"):
        # Force LLM API call to throw an exception
        with patch("httpx.Client.post", side_effect=httpx.HTTPError("Gemini server error")):
            # Document has standard info and term but lacks governing law
            text = (
                "Mutual Non-Disclosure Agreement.\n"
                "Confidentiality: Recipient agrees to protect Confidential Information.\n"
                "Term: This agreement ends in 3 years."
            )

            result = compliance_service.check_compliance(text, "standard_nda")

            # Since LLM failed, fallback keyword checker runs
            assert result["status"] == "non-compliant"
            assert any("Missing Governing Law or Jurisdiction" in v for v in result["violations"])


def test_compliance_auto_detection():
    """
    Test that detect_rule_set accurately determines rule sets from content and filenames.
    """
    service = ComplianceService()

    assert service.detect_rule_set("This is a mutual non-disclosure agreement.", "nda.pdf") == "standard_nda"
    assert service.detect_rule_set("Data processor shall handle personal data under GDPR.", "dpa.docx") == "gdpr_privacy"
    assert service.detect_rule_set("The employer agrees to pay employee standard salary.", "offer_letter.pdf") == "employment_agreement"
    assert service.detect_rule_set("Franchisor grants exclusive territory to franchisee.", "franchise.pdf") == "franchise_agreement"
    assert service.detect_rule_set("Landlord leases the premises to tenant.", "lease_agreement.pdf") == "commercial_lease"
    assert service.detect_rule_set("Customer data is hosted in SaaS cloud under standard SLA.", "saas_agreement.pdf") == "saas_service_agreement"


def test_compliance_endpoint_auto_detection_and_internal_token():
    """
    Test POST /api/v1/documents/{document_id}/compliance endpoint:
    1. Called with internal service token (X-Internal-Token).
    2. Auto-detects rule_set if omitted.
    3. Persists results to compliance_checks table and audit log.
    """
    import uuid
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import SessionLocal
    from app.models.database_models import Document, ExtractedText, ComplianceCheck, AuditLog
    from app.api.v1.routers.documents import ensure_test_user_exists
    from app.core.config import settings

    client = TestClient(app)
    db = SessionLocal()
    doc_id = uuid.uuid4()

    try:
        user_id = ensure_test_user_exists(db)

        doc = Document(
            id=doc_id,
            user_id=user_id,
            filename="data_processing_addendum.pdf",
            status="uploaded"
        )
        db.add(doc)
        db.commit()

        text_obj = ExtractedText(
            id=uuid.uuid4(),
            document_id=doc_id,
            content="""DATA PROCESSING AGREEMENT
This Data Processing Addendum governs personal data processing under GDPR.
1. Security: Data processor shall implement technical and organisational security measures including encryption.
2. Breach Notification: Data processor shall notify controller within 72 hours without undue delay.
3. Sub-processors: Prior written authorization required for sub-processors.
""",
            method="native",
            parsing_confidence=1.0
        )
        db.add(text_obj)
        db.commit()

        # 1. Test call with internal service token and NO rule_set specified (auto-detection)
        headers = {"x-internal-token": settings.INTERNAL_SERVICE_TOKEN}
        response = client.post(f"/api/v1/documents/{doc_id}/compliance", json={}, headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == str(doc_id)
        assert data["auto_detected"] is True
        assert data["rule_set"] == "gdpr_privacy"
        assert isinstance(data["violations"], list)
        assert data["status"] in ["compliant", "non-compliant"]

        # Verify ComplianceCheck row stored in database
        comp_check = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc_id).first()
        assert comp_check is not None
        assert comp_check.rule_set == "gdpr_privacy"

        # 2. Test call with explicit rule_set parameter
        response2 = client.post(
            f"/api/v1/documents/{doc_id}/compliance",
            json={"rule_set": "standard_nda"},
            headers=headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["auto_detected"] is False
        assert data2["rule_set"] == "standard_nda"

    finally:
        # Cleanup
        db.query(AuditLog).filter(AuditLog.document_id == doc_id).delete()
        db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc_id).delete()
        db.query(ExtractedText).filter(ExtractedText.document_id == doc_id).delete()
        db.query(Document).filter(Document.id == doc_id).delete()
        db.commit()
        db.close()


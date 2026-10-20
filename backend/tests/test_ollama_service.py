"""
test_ollama_service.py
Unit tests for ollama_service.py.

Verifies:
1. JSON cleaning logic (fences, commentary, <think> tags).
2. Health-check reachability (empty URL, connection failure, healthy 200).
3. Graceful failure when Ollama is unreachable.
4. Retry-on-invalid-JSON behavior (retry prompt instruction and giving up on repeated failure).
5. The 5 master prompt methods (classify_document, extract_entities, analyze_clause_risk,
   audit_compliance, generate_summary).
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Ensure backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ollama_service import (
    OllamaService,
    clean_json_string,
)

# =============================================================================
# 1. JSON Cleaning Logic Tests
# =============================================================================

def test_clean_json_string_plain():
    """Verify plain JSON with leading/trailing whitespace is parsed correctly."""
    raw = '   {"status": "ok", "count": 5}   \n'
    assert clean_json_string(raw) == '{"status": "ok", "count": 5}'


def test_clean_json_string_markdown_fence():
    """Verify markdown code fence with language tag is stripped."""
    raw = (
        "```json\n"
        '{\n  "document_type": "Non-Disclosure Agreement",\n  "confidence": 0.95\n}\n'
        "```"
    )
    cleaned = clean_json_string(raw)
    parsed = json.loads(cleaned)
    assert parsed["document_type"] == "Non-Disclosure Agreement"
    assert parsed["confidence"] == 0.95


def test_clean_json_string_markdown_fence_no_tag():
    """Verify markdown code fence without language tag is stripped."""
    raw = "```\n" '{"severity": "HIGH", "issue": "Uncapped indemnity"}\n' "```"
    cleaned = clean_json_string(raw)
    parsed = json.loads(cleaned)
    assert parsed["severity"] == "HIGH"


def test_clean_json_string_with_conversational_text():
    """Verify leading and trailing conversational text is stripped."""
    raw = (
        "Here is the requested legal analysis in JSON format:\n\n"
        '{\n  "status": "compliant",\n  "safety_score": 90\n}\n\n'
        "Please let me know if you need further clarification."
    )
    cleaned = clean_json_string(raw)
    parsed = json.loads(cleaned)
    assert parsed["status"] == "compliant"
    assert parsed["safety_score"] == 90


def test_clean_json_string_with_think_tags():
    """Verify reasoning <think>...</think> tags emitted by reasoning models are removed."""
    raw = (
        "<think>The user wants to classify an agreement. The text mentions proprietary data.</think>\n"
        '```json\n{"document_type": "NDA", "confidence": 0.88}\n```'
    )
    cleaned = clean_json_string(raw)
    parsed = json.loads(cleaned)
    assert parsed["document_type"] == "NDA"
    assert parsed["confidence"] == 0.88


def test_clean_json_string_empty_raises():
    """Verify empty or whitespace-only strings raise ValueError."""
    with pytest.raises(ValueError):
        clean_json_string("")
    with pytest.raises(ValueError):
        clean_json_string("   \n\t  ")


# =============================================================================
# 2. Health-Check & Reachability Tests
# =============================================================================

def test_health_check_empty_url(monkeypatch):
    """Verify check_health returns False when OLLAMA_BASE_URL is unset or empty."""
    monkeypatch.setattr("app.services.ollama_service.settings.OLLAMA_BASE_URL", "")
    assert OllamaService.check_health() is False
    assert OllamaService.check_health(base_url="") is False


def test_health_check_unreachable():
    """Verify check_health gracefully returns False when connection fails."""
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        assert OllamaService.check_health(base_url="http://localhost:11434") is False


def test_health_check_reachable():
    """Verify check_health returns True when Ollama /api/version responds with 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"version": "0.5.1"}

    with patch("httpx.Client.get", return_value=mock_resp):
        assert OllamaService.check_health(base_url="http://localhost:11434") is True


def test_graceful_failure_when_ollama_unreachable():
    """Verify API methods raise ConnectionError when Ollama is unreachable."""
    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(ConnectionError, match="Failed to connect to Ollama"):
            OllamaService.classify_document("Sample NDA text", base_url="http://localhost:11434")


def test_graceful_failure_when_url_empty(monkeypatch):
    """Verify API methods raise ConnectionError when base_url is unconfigured."""
    monkeypatch.setattr("app.services.ollama_service.settings.OLLAMA_BASE_URL", "")
    with pytest.raises(ConnectionError, match="not configured or empty"):
        OllamaService.classify_document("Sample NDA text", base_url="")


# =============================================================================
# 3. Retry-on-Invalid-JSON Behavior Tests
# =============================================================================

def test_retry_on_invalid_json_succeeds():
    """
    Verify that when Ollama initially returns invalid JSON, it retries once
    with the explicit 'your previous response was invalid JSON, fix it'
    instruction and successfully returns the corrected JSON.
    """
    first_resp = MagicMock()
    first_resp.status_code = 200
    first_resp.json.return_value = {"response": "Here is the result: {broken json missing close"}

    second_resp = MagicMock()
    second_resp.status_code = 200
    second_resp.json.return_value = {
        "response": json.dumps({
            "document_type": "Non-Disclosure Agreement",
            "confidence": 0.95,
            "summary_category": "Confidentiality",
            "key_indicators": ["Confidential Information", "Non-disclosure"]
        })
    }

    with patch("httpx.Client.post", side_effect=[first_resp, second_resp]) as mock_post:
        result = OllamaService.classify_document("Contract text", base_url="http://localhost:11434")

        # Verify exactly 2 calls were made (1 original + 1 retry)
        assert mock_post.call_count == 2

        # Verify the retry prompt contained the required correction instruction
        retry_call_args = mock_post.call_args_list[1]
        retry_payload = retry_call_args.kwargs.get("json") or retry_call_args[1].get("json")
        assert "your previous response was invalid json, fix it" in retry_payload["prompt"].lower()

        # Verify final result matches expected structure
        assert result["document_type"] == "Non-Disclosure Agreement"
        assert result["confidence"] == 0.95
        assert result["summary_category"] == "Confidentiality"


def test_retry_on_invalid_json_gives_up():
    """
    Verify that if both initial call and retry fail to return valid JSON,
    the service gives up and raises a ValueError.
    """
    first_resp = MagicMock()
    first_resp.status_code = 200
    first_resp.json.return_value = {"response": "Malformed text 1"}

    second_resp = MagicMock()
    second_resp.status_code = 200
    second_resp.json.return_value = {"response": "Malformed text 2"}

    with patch("httpx.Client.post", side_effect=[first_resp, second_resp]) as mock_post:
        with pytest.raises(ValueError, match="invalid JSON after retry"):
            OllamaService.classify_document("Contract text", base_url="http://localhost:11434")

        # Confirm exactly 2 attempts were executed before giving up
        assert mock_post.call_count == 2


# =============================================================================
# 4. Master Prompts Execution Tests
# =============================================================================

def test_classify_document_method():
    """Verify classify_document returns a valid DocumentClassification typed dict."""
    mock_payload = {
        "document_type": "Software License Agreement",
        "confidence": 0.92,
        "summary_category": "Intellectual Property",
        "key_indicators": ["License Grant", "Proprietary Rights"]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_payload)}

    with patch("httpx.Client.post", return_value=mock_resp):
        res = OllamaService.classify_document("Sample SLA text", base_url="http://localhost:11434")
        assert res["document_type"] == "Software License Agreement"
        assert res["confidence"] == 0.92
        assert res["summary_category"] == "Intellectual Property"
        assert "License Grant" in res["key_indicators"]


def test_extract_entities_method():
    """Verify extract_entities returns ExtractedEntities matching DealTermsResponse."""
    mock_payload = {
        "parties": ["Acme Corp", "Tech Solutions LLC"],
        "effective_date": "2025-01-01",
        "expiration_date": "2027-01-01",
        "auto_renewal": True,
        "renewal_notice_days": 60,
        "governing_law": "Delaware",
        "jurisdiction": "New Castle County",
        "document_type": "Master Services Agreement",
        "key_amounts": ["$50,000 annual fee", "1.5% late interest"]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_payload)}

    with patch("httpx.Client.post", return_value=mock_resp):
        res = OllamaService.extract_entities("Sample MSA text", base_url="http://localhost:11434")
        assert res["parties"] == ["Acme Corp", "Tech Solutions LLC"]
        assert res["effective_date"] == "2025-01-01"
        assert res["auto_renewal"] is True
        assert res["renewal_notice_days"] == 60
        assert res["governing_law"] == "Delaware"
        assert len(res["key_amounts"]) == 2


def test_analyze_clause_risk_method():
    """Verify analyze_clause_risk returns ClauseRiskAnalysis schema."""
    mock_payload = {
        "type": "Indemnification",
        "severity": "HIGH",
        "explanation": "Uncapped indemnification obligation with no reciprocal indemnity.",
        "issue": "Unlimited third-party liability exposure.",
        "recommendation": "Add a mutual liability cap and carve out indirect damages.",
        "confidence_score": 0.95
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_payload)}

    with patch("httpx.Client.post", return_value=mock_resp):
        res = OllamaService.analyze_clause_risk(
            clause_text="Party A agrees to indemnify Party B unconditionally.",
            clause_type="Indemnity",
            base_url="http://localhost:11434"
        )
        assert res["type"] == "Indemnification"
        assert res["severity"] == "HIGH"
        assert "Uncapped" in res["explanation"]
        assert res["confidence_score"] == 0.95


def test_audit_compliance_method():
    """Verify audit_compliance returns ComplianceAuditResult schema."""
    mock_payload = {
        "status": "non-compliant",
        "rule_set": "standard_nda",
        "violations": ["Term of confidentiality is perpetual with no carve-outs."],
        "missing_clauses": ["Return or destruction of confidential materials."],
        "safety_score": 45,
        "risk_level": "HIGH"
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps(mock_payload)}

    with patch("httpx.Client.post", return_value=mock_resp):
        res = OllamaService.audit_compliance(
            document_text="Sample contract terms.",
            rule_set="standard_nda",
            base_url="http://localhost:11434"
        )
        assert res["status"] == "non-compliant"
        assert res["rule_set"] == "standard_nda"
        assert len(res["violations"]) == 1
        assert len(res["missing_clauses"]) == 1
        assert res["safety_score"] == 45
        assert res["risk_level"] == "HIGH"


def test_generate_summary_method():
    """
    Verify generate_summary calls /api/generate WITHOUT 'format': 'json'
    and returns a clean prose string.
    """
    prose_summary = (
        "This Mutual Non-Disclosure Agreement establishes confidentiality obligations "
        "between the parties for evaluating mutual business opportunities. Each party "
        "commits to protect confidential information with standard care for two years."
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": prose_summary}

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        res = OllamaService.generate_summary(
            document_text="Full agreement content...",
            base_url="http://localhost:11434"
        )
        # Verify result is pure prose string
        assert isinstance(res, str)
        assert "Mutual Non-Disclosure Agreement" in res

        # Verify format: json was NOT passed in the payload
        post_kwargs = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert "format" not in post_kwargs


# =============================================================================
# 5. Ollama Timeout & num_ctx Payload Verification Tests
# =============================================================================

def test_ollama_payload_includes_num_ctx_and_timeout():
    """
    Verify that OllamaService calls httpx.Client with at least 120s timeout,
    and includes num_ctx=4096 in options to prevent VRAM overflow.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": json.dumps({"status": "ok"})}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        OllamaService._call_generate("Test prompt", base_url="http://localhost:11434")

        # Verify Client initialized with at least 120 seconds
        assert mock_client_cls.call_args is not None
        timeout_arg = mock_client_cls.call_args.kwargs.get("timeout")
        assert timeout_arg >= 120.0

        # Verify payload options contains num_ctx = 4096
        post_args = mock_client.post.call_args
        payload = post_args.kwargs.get("json") or post_args[1].get("json")
        assert payload["options"]["num_ctx"] == 4096
        assert payload["num_ctx"] == 4096


def test_llm_service_execute_ollama_request():
    """
    Verify LLMService._execute_ollama_request passes timeout >= 120s and num_ctx=4096.
    """
    from app.services.llm_service import LLMService
    service = LLMService()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "{\"status\": \"ok\"}"}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        service._execute_ollama_request("Sample prompt")

        timeout_arg = mock_client_cls.call_args.kwargs.get("timeout")
        assert timeout_arg >= 120.0

        payload = mock_client.post.call_args.kwargs.get("json")
        assert payload["options"]["num_ctx"] == 4096


def test_llm_service_analyze_contract_sends_chunk_text():
    """
    Verify LLMService.analyze_contract sends the specific chunk_text to Ollama,
    rather than embedding the entire document text.
    """
    from app.services.llm_service import LLMService
    service = LLMService()

    full_document = (
        "Article 1. Preamble and Definitions\nThis is the first long section.\n\n"
        "Article 2. Confidentiality\nRecipient must keep information confidential.\n\n"
        "Article 3. Limitation of Liability\nNeither party liable for consequential damages."
    )
    specific_chunk = "Article 2. Confidentiality\nRecipient must keep information confidential."

    mock_ollama_data = {
        "summary": "Ollama analyzed chunk.",
        "document_overview": "Confidentiality clause overview.",
        "plain_english_summary": "Recipient keeps secrets safe.",
        "parties": ["Alpha Corp", "Beta LLC"],
        "key_dates": {"effective_date": "2025-01-01"},
        "missing_sections": [],
        "safety_score": 90,
        "risk_level": "LOW",
        "clauses": [{
            "clause_type": "Confidentiality Obligations",
            "clause_text": specific_chunk,
            "severity": "LOW",
            "explanation": "Standard confidentiality terms.",
            "category": "Confidentiality & IP",
            "confidence_score": 0.95
        }],
        "citations": [],
        "recommendations": []
    }

    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "_generate_json_with_retry", return_value=mock_ollama_data) as mock_gen:
        result = service.analyze_contract(full_document, chunk_text=specific_chunk)

        assert result["summary"] == "Ollama analyzed chunk."
        prompt_arg = mock_gen.call_args[0][0]
        # Specific chunk MUST be present
        assert specific_chunk in prompt_arg
        # Other articles from full document MUST NOT be in Ollama prompt
        assert "Article 3. Limitation of Liability" not in prompt_arg


def test_llm_service_analyze_contract_chunks_full_document_when_chunk_not_provided():
    """
    Verify that when chunk_text is not provided, LLMService uses legal_chunker
    and sends the first chunk rather than the entire multi-article document to Ollama.
    """
    from app.services.llm_service import LLMService
    service = LLMService()

    multi_article_doc = (
        "Article 1. Preamble and Definitions\nThis is the preamble.\n\n"
        "Article 2. Scope of Services\nVendor provides development services.\n\n"
        "Article 3. Governing Law\nGoverned by laws of California."
    )

    mock_ollama_data = {
        "summary": "Ollama analyzed chunk 1.",
        "document_overview": "Preamble overview.",
        "plain_english_summary": "Defines agreement scope.",
        "parties": ["Party A", "Party B"],
        "key_dates": {},
        "missing_sections": [],
        "safety_score": 85,
        "risk_level": "LOW",
        "clauses": [{
            "clause_type": "Preamble",
            "clause_text": "Article 1. Preamble and Definitions",
            "severity": "LOW",
            "explanation": "Standard terms.",
            "category": "General",
            "confidence_score": 0.90
        }],
        "citations": [],
        "recommendations": []
    }

    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "_generate_json_with_retry", return_value=mock_ollama_data) as mock_gen:
        result = service.analyze_contract(multi_article_doc)

        assert result["summary"] == "Ollama analyzed chunk 1."
        prompt_arg = mock_gen.call_args[0][0]
        # First chunk should be present
        assert "Article 1. Preamble and Definitions" in prompt_arg
        # Subsequent chunk must NOT be present in Ollama prompt
        assert "Article 2. Scope of Services" not in prompt_arg


def test_llm_service_ollama_timeout_fallback_to_gemini():
    """
    Verify that when Ollama raises a connection/read timeout error,
    it logs and gracefully falls back to Gemini without failing.
    """
    from app.services.llm_service import LLMService
    service = LLMService()

    mock_gemini_data = {
        "summary": "Gemini analyzed agreement after Ollama timed out.",
        "document_overview": "Overview from Gemini.",
        "plain_english_summary": "Plain English summary from Gemini.",
        "parties": ["Alpha", "Beta"],
        "key_dates": {"effective_date": "2025-01-01"},
        "missing_sections": [],
        "safety_score": 80,
        "risk_level": "LOW",
        "clauses": [{
            "clause_type": "Confidentiality Obligations",
            "clause_text": "Sample text",
            "severity": "LOW",
            "explanation": "Safe terms",
            "category": "Confidentiality & IP",
            "confidence_score": 0.95
        }],
        "citations": [],
        "recommendations": []
    }

    with patch.object(OllamaService, "check_health", return_value=True), \
         patch.object(OllamaService, "_generate_json_with_retry", side_effect=ConnectionError("Failed to connect to Ollama at http://localhost:11434: timed out")), \
         patch.object(service, "_call_gemini", return_value=mock_gemini_data):
        result = service.analyze_contract("Sample contract text")
        assert result["summary"] == "Gemini analyzed agreement after Ollama timed out."


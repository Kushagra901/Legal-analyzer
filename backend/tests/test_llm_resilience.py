"""
Tests for LLM API call retries and fallback handling using tenacity.
"""
from unittest.mock import MagicMock, patch

import httpx

from app.services.llm_service import LLMService, _is_retryable_exception


def test_is_retryable_exception():
    res_429 = MagicMock(status_code=429)
    res_500 = MagicMock(status_code=500)
    res_502 = MagicMock(status_code=502)
    res_503 = MagicMock(status_code=503)
    res_504 = MagicMock(status_code=504)
    res_400 = MagicMock(status_code=400)

    assert _is_retryable_exception(httpx.HTTPStatusError("Rate Limit", request=MagicMock(), response=res_429)) is True
    assert _is_retryable_exception(httpx.HTTPStatusError("Server Error", request=MagicMock(), response=res_500)) is True
    assert _is_retryable_exception(httpx.HTTPStatusError("Bad Gateway", request=MagicMock(), response=res_502)) is True
    assert _is_retryable_exception(httpx.HTTPStatusError("Service Unavailable", request=MagicMock(), response=res_503)) is True
    assert _is_retryable_exception(httpx.HTTPStatusError("Gateway Timeout", request=MagicMock(), response=res_504)) is True
    assert _is_retryable_exception(httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=res_400)) is False

    assert _is_retryable_exception(httpx.ConnectError("Connection failed")) is True


def test_llm_service_retries_on_transient_failure_then_succeeds():
    service = LLMService()
    service.api_key = "test-api-key"

    fail_res = MagicMock()
    fail_res.status_code = 500
    fail_exception = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=fail_res)

    success_res = MagicMock()
    success_res.status_code = 200
    success_res.raise_for_status = MagicMock()
    success_res.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": '{"summary": "Retried summary", "safety_score": 100, "risk_level": "LOW", "clauses": [], "citations": [], "recommendations": []}'
                }]
            }
        }]
    }

    with patch("httpx.Client.post", side_effect=[fail_exception, success_res]):
        result = service.analyze_contract("Sample contract text")
        assert result["summary"] == "Retried summary"


def test_llm_service_falls_back_when_all_retries_exhausted():
    service = LLMService()
    service.api_key = "test-api-key"

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Network offline")):
        result = service.analyze_contract("confidential disclosure")
        assert "Offline rule-based fallback analysis" in result["summary"]

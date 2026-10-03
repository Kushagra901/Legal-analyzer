"""
Tests for n8n Webhook Trigger Authentication and Workflow Configuration.
Label: SEC-OPS-001-N8N-WEBHOOK-AUTH
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.routers.documents.crud import trigger_n8n_webhook
from app.core.config import settings


@pytest.mark.anyio
async def test_trigger_n8n_webhook_sends_auth_headers():
    """
    Verify that trigger_n8n_webhook sends the X-Webhook-Secret header
    populated with settings.INTERNAL_SERVICE_TOKEN.
    """
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        await trigger_n8n_webhook(
            document_id="doc-12345",
            filename="contract.pdf",
            email="lawyer@example.com"
        )

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs

        assert "headers" in call_kwargs
        headers = call_kwargs["headers"]
        assert headers.get("X-Webhook-Secret") == settings.INTERNAL_SERVICE_TOKEN
        assert headers.get("Content-Type") == "application/json"

        assert call_kwargs["json"] == {
            "document_id": "doc-12345",
            "filename": "contract.pdf",
            "email": "lawyer@example.com"
        }


def test_n8n_workflow_json_header_auth_and_token_expressions():
    """
    Verify that n8n_workflow.json:
    1. Sets webhook-trigger authentication to headerAuth.
    2. Configures header verification for X-Webhook-Secret matching $env.INTERNAL_SERVICE_TOKEN.
    3. Replaces all hardcoded placeholder_internal_service_token values with $env expressions.
    """
    # Locate n8n_workflow.json in project root
    workflow_path = Path(__file__).resolve().parent.parent.parent / "n8n_workflow.json"
    assert workflow_path.exists(), f"n8n_workflow.json not found at {workflow_path}"

    with open(workflow_path, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Verify webhook-trigger node
    webhook_node = next((n for n in data.get("nodes", []) if n.get("id") == "webhook-trigger"), None)
    assert webhook_node is not None, "webhook-trigger node not found in n8n_workflow.json"

    params = webhook_node.get("parameters", {})
    assert params.get("authentication") == "headerAuth"
    assert "headerAuth" in params or "credentials" in webhook_node

    if "headerAuth" in params:
        header_auth = params["headerAuth"]
        assert header_auth.get("name") == "X-Webhook-Secret"
        assert header_auth.get("value") == "={{ $env.INTERNAL_SERVICE_TOKEN }}"

    # 2. Verify no remaining hardcoded placeholder_internal_service_token
    raw_content = workflow_path.read_text(encoding="utf-8")
    assert "placeholder_internal_service_token" not in raw_content

    # 3. Verify at least one HTTP Request node sends $env.INTERNAL_SERVICE_TOKEN
    assert "={{ $env.INTERNAL_SERVICE_TOKEN }}" in raw_content

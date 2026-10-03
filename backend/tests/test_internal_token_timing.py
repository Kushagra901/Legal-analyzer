"""
Unit tests for constant-time internal service token comparison.
Verifies SEC-AUTH-002-TIMING-ATTACK-DEFENSE requirements.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import get_current_user
from app.core.config import settings


def test_valid_internal_service_token_succeeds(monkeypatch):
    """
    Ensure a matching x-internal-token authenticates as the system admin user.
    """
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", "super-secret-service-token-12345")

    mock_request = MagicMock()
    mock_request.headers = {"x-internal-token": "super-secret-service-token-12345"}
    mock_db = MagicMock()

    user = get_current_user(
        request=mock_request,
        credentials=None,
        db=mock_db,
        supabase_client=None,
    )

    assert user.role == "admin"
    assert user.email == "system-internal@service.local"
    assert user.id == uuid.UUID("00000000-0000-0000-0000-000000000000")


def test_invalid_internal_service_token_raises_401(monkeypatch):
    """
    Ensure mismatched x-internal-token raises HTTP 401.
    """
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", "super-secret-service-token-12345")

    mock_request = MagicMock()
    mock_request.headers = {"x-internal-token": "wrong-token-value"}
    mock_db = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            request=mock_request,
            credentials=None,
            db=mock_db,
            supabase_client=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid internal service token."


def test_constant_time_comparison_used(monkeypatch):
    """
    Verify hmac.compare_digest is utilized during token verification.
    """
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", "correct-token")

    mock_request = MagicMock()
    mock_request.headers = {"x-internal-token": "correct-token"}
    mock_db = MagicMock()

    with patch("app.core.auth.hmac.compare_digest", return_value=True) as mock_compare:
        get_current_user(
            request=mock_request,
            credentials=None,
            db=mock_db,
            supabase_client=None,
        )
        mock_compare.assert_called_once_with("correct-token", "correct-token")

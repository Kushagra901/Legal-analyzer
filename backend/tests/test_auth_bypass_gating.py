"""
Unit tests for mock authentication gating behind ENVIRONMENT.
Verifies SEC-AUTH-001-MOCK-BYPASS requirements.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import get_current_user
from app.core.config import settings
from app.models import Organization, User


def test_mock_auth_blocked_in_production(monkeypatch):
    """
    Ensure mock authentication tokens ('mock-token', 'test-token', AUTH_MOCK_TOKEN)
    raise HTTP 401 in production environment.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_db = MagicMock()
    mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            request=mock_request,
            credentials=mock_credentials,
            db=mock_db,
            supabase_client=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Mock authentication is strictly disabled in production."


def test_mock_auth_blocked_in_production_case_insensitive(monkeypatch):
    """
    Ensure environment check is case-insensitive ('PRODUCTION', 'Production').
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "PRODUCTION")

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_db = MagicMock()
    mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            request=mock_request,
            credentials=mock_credentials,
            db=mock_db,
            supabase_client=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Mock authentication is strictly disabled in production."


def test_mock_auth_allowed_in_development_and_testing(monkeypatch):
    """
    Ensure mock authentication succeeds in 'development' and 'testing' environments.
    """
    for env in ("development", "testing"):
        monkeypatch.setattr(settings, "ENVIRONMENT", env)

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_db = MagicMock()

        # Mock existing org and user in DB
        fake_org = Organization(id=settings.AUTH_MOCK_TOKEN, name="Test Org", plan="free")
        fake_user = User(email="test@example.com", role="user")

        mock_db.query.return_value.filter.return_value.first.side_effect = [fake_org, fake_user]
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")

        user = get_current_user(
            request=mock_request,
            credentials=mock_credentials,
            db=mock_db,
            supabase_client=None,
        )

        assert user == fake_user

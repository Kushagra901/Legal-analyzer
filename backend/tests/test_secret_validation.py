"""
Unit tests for production startup secrets guard.
Verifies SEC-CFG-002-SECRET-VALIDATION requirements.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


def test_production_secret_key_placeholder_fails():
    """
    Ensure RuntimeError is raised when ENVIRONMENT is production and SECRET_KEY is placeholder.
    """
    custom_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="placeholder_secret_key_change_me_in_production",
        INTERNAL_SERVICE_TOKEN="secure_random_production_service_token_value_here",
    )
    with pytest.raises(RuntimeError) as exc_info:
        custom_settings.validate_production_secrets()

    assert "FATAL: Production launch halted" in str(exc_info.value)
    assert "SECRET_KEY" in str(exc_info.value)


def test_production_internal_service_token_placeholder_fails():
    """
    Ensure RuntimeError is raised when ENVIRONMENT is production and INTERNAL_SERVICE_TOKEN is placeholder.
    """
    custom_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure_random_production_secret_key_value_here",
        INTERNAL_SERVICE_TOKEN="placeholder_internal_service_token_change_me",
    )
    with pytest.raises(RuntimeError) as exc_info:
        custom_settings.validate_production_secrets()

    assert "FATAL: Production launch halted" in str(exc_info.value)
    assert "INTERNAL_SERVICE_TOKEN" in str(exc_info.value)


def test_production_both_placeholders_fail():
    """
    Ensure both insecure secrets are listed in the fatal error message.
    """
    custom_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="placeholder_secret_key_change_me_in_production",
        INTERNAL_SERVICE_TOKEN="placeholder_internal_service_token_change_me",
    )
    with pytest.raises(RuntimeError) as exc_info:
        custom_settings.validate_production_secrets()

    assert "SECRET_KEY, INTERNAL_SERVICE_TOKEN" in str(exc_info.value)


def test_production_empty_secrets_fail():
    """
    Ensure empty string secrets also trigger production halt.
    """
    custom_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="",
        INTERNAL_SERVICE_TOKEN="",
    )
    with pytest.raises(RuntimeError) as exc_info:
        custom_settings.validate_production_secrets()

    assert "SECRET_KEY, INTERNAL_SERVICE_TOKEN" in str(exc_info.value)


def test_production_valid_secrets_pass():
    """
    Ensure production startup check passes when secure secrets are configured.
    """
    custom_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="e9b25f1624c96b797b102927237936a287239ef7190d649ab0e9a7e671d18258",
        INTERNAL_SERVICE_TOKEN="0b355883ef873c9f28c253818e8dc4627d3fa8f01a3cfb8b7e2c9ef89736f874",
    )
    # Should not raise
    custom_settings.validate_production_secrets()


def test_development_and_testing_allow_placeholders():
    """
    Ensure non-production environments allow default placeholder secrets without error.
    """
    for env in ("development", "testing"):
        custom_settings = Settings(
            ENVIRONMENT=env,
            SECRET_KEY="placeholder_secret_key_change_me_in_production",
            INTERNAL_SERVICE_TOKEN="placeholder_internal_service_token_change_me",
        )
        # Should not raise
        custom_settings.validate_production_secrets()


def test_fastapi_lifespan_enforces_production_secrets_guard(monkeypatch):
    """
    Ensure FastAPI startup lifespan triggers validation and prevents boot in production with placeholders.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "placeholder_secret_key_change_me_in_production")

    with pytest.raises(RuntimeError) as exc_info:
        with TestClient(app):
            pass

    assert "FATAL: Production launch halted" in str(exc_info.value)

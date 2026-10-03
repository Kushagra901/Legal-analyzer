"""
Pytest configuration and global fixtures.
Ensures the test suite defaults to ENVIRONMENT='testing'.
"""

import os

import pytest

# Ensure environment variable and settings are set to testing for all test suites
os.environ["ENVIRONMENT"] = "testing"

from app.core.config import settings
from app.core.limiter import limiter

settings.ENVIRONMENT = "testing"


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """
    Autouse fixture ensuring settings.ENVIRONMENT defaults to 'testing' across tests
    and resetting rate limits between test executions.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "testing")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    limiter.reset()

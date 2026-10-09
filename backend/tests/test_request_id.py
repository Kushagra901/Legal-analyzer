"""
Unit tests for RequestIDMiddleware.
Validates generation, propagation, and preservation of X-Request-ID correlation headers.
"""

import uuid
from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_id_generated_when_missing():
    """
    Ensure an X-Request-ID header is generated if not provided in the request.
    """
    response = client.get("/health")
    assert response.status_code == 200
    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    # Validate it's a valid UUID
    parsed_uuid = uuid.UUID(request_id)
    assert str(parsed_uuid) == request_id


def test_request_id_preserved_when_provided():
    """
    Ensure an incoming X-Request-ID header is preserved and returned in the response.
    """
    custom_id = "test-request-id-abcd-1234"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


def test_request_id_uniqueness():
    """
    Ensure consecutive requests without an explicit X-Request-ID receive distinct IDs.
    """
    response1 = client.get("/health")
    response2 = client.get("/health")
    assert response1.headers.get("x-request-id") != response2.headers.get("x-request-id")

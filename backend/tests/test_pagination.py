"""
Unit tests for limit/offset pagination on list endpoints.
Validates API-REST-001-PAGINATION requirements.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import AuditLog, Document, User

# In-memory SQLite for pagination testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ADMIN_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_regular_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="regular@example.com", role="user")


def override_get_admin_user():
    return User(id=ADMIN_USER_ID, org_id=ADMIN_USER_ID, email="admin@example.com", role="admin")


def setup_function():
    """Seed test documents and audit logs before tests."""
    db = TestingSessionLocal()
    db.query(Document).delete()
    db.query(AuditLog).delete()
    db.commit()

    now = datetime.now(UTC)
    for i in range(5):
        doc = Document(
            id=uuid.uuid4(),
            filename=f"contract_{i}.pdf",
            user_id=TEST_USER_ID,
            status="completed",
            uploaded_at=now - timedelta(minutes=i),
        )
        db.add(doc)

    for i in range(7):
        log = AuditLog(
            id=uuid.uuid4(),
            action=f"Action event {i}",
            created_at=now - timedelta(minutes=i),
        )
        db.add(log)

    db.commit()
    db.close()


def test_list_documents_default_pagination():
    """Verify GET /api/v1/documents returns default limit=50 and offset=0 with total count."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_regular_user
    try:
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 5
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["items"]) == 5
    finally:
        app.dependency_overrides.clear()


def test_list_documents_custom_limit_and_offset():
    """Verify limit and offset query parameters slice documents correctly."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_regular_user
    try:
        # First page with limit 2
        resp1 = client.get("/api/v1/documents?limit=2&offset=0")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["total"] == 5
        assert data1["limit"] == 2
        assert data1["offset"] == 0
        assert len(data1["items"]) == 2
        first_doc = data1["items"][0]["filename"]

        # Second page with limit 2, offset 2
        resp2 = client.get("/api/v1/documents?limit=2&offset=2")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["total"] == 5
        assert len(data2["items"]) == 2
        assert data2["items"][0]["filename"] != first_doc

        # Third page with limit 2, offset 4
        resp3 = client.get("/api/v1/documents?limit=2&offset=4")
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert data3["total"] == 5
        assert len(data3["items"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_list_documents_limit_enforcement():
    """Verify limit exceeding 100 or offset < 0 is rejected with 422."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_regular_user
    try:
        # limit > 100
        resp_over = client.get("/api/v1/documents?limit=101")
        assert resp_over.status_code == 422

        # offset < 0
        resp_neg = client.get("/api/v1/documents?offset=-1")
        assert resp_neg.status_code == 422

        # limit < 1
        resp_zero = client.get("/api/v1/documents?limit=0")
        assert resp_zero.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_get_audit_logs_default_pagination():
    """Verify GET /api/v1/admin/audit-logs returns default limit=50 and offset=0 with total count."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_admin_user
    try:
        response = client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 7
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["items"]) == 7
    finally:
        app.dependency_overrides.clear()


def test_get_audit_logs_custom_limit_and_offset():
    """Verify limit and offset query parameters slice audit logs correctly."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_admin_user
    try:
        resp = client.get("/api/v1/admin/audit-logs?limit=3&offset=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert data["limit"] == 3
        assert data["offset"] == 2
        assert len(data["items"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_get_audit_logs_limit_enforcement():
    """Verify audit-logs endpoint enforces limit <= 100 and offset >= 0."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_admin_user
    try:
        resp_over = client.get("/api/v1/admin/audit-logs?limit=101")
        assert resp_over.status_code == 422

        resp_neg = client.get("/api/v1/admin/audit-logs?offset=-1")
        assert resp_neg.status_code == 422
    finally:
        app.dependency_overrides.clear()

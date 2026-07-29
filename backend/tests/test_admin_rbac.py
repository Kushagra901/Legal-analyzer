import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import AuditLog, Clause, ComplianceCheck, Document, RiskFlag, User  # noqa: F401

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_regular_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="user@example.com", role="user")


def override_get_admin_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="admin@example.com", role="admin")


def test_admin_audit_logs_forbidden_for_regular_user():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_regular_user
    try:
        response = client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_audit_logs_allowed_for_admin():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_admin_user
    try:
        response = client.get("/api/v1/admin/audit-logs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()

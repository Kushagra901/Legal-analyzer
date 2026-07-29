"""
Unit tests for asynchronous document analysis tasks and GET /status endpoint.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import Clause, Document, ExtractedText, User
from app.workers.tasks import execute_document_analysis

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return User(
        id=USER_ID,
        org_id=USER_ID,
        email="test@example.com",
        role="user"
    )


@pytest.fixture(autouse=True)
def setup_overrides():
    old_db = app.dependency_overrides.get(get_db)
    old_user = app.dependency_overrides.get(get_current_user)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    db.query(Document).delete()
    db.commit()
    db.close()

    yield

    if old_db:
        app.dependency_overrides[get_db] = old_db
    else:
        app.dependency_overrides.pop(get_db, None)

    if old_user:
        app.dependency_overrides[get_current_user] = old_user
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_async_task_execution(monkeypatch):
    """
    Test executing document analysis background task.
    """
    monkeypatch.setattr("app.workers.tasks.SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    doc = Document(
        id=uuid.uuid4(),
        filename="async_contract.pdf",
        user_id=USER_ID,
        status="processing"
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="This Agreement is governed by the laws of California. Neither party is liable for damages.",
        method="native"
    )
    db.add(extracted)
    db.commit()
    db.close()

    # Execute async analysis logic
    execute_document_analysis(doc_id)

    db = TestingSessionLocal()
    updated_doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()
    assert updated_doc is not None
    assert updated_doc.status == "completed"
    assert updated_doc.safety_score is not None

    clauses = db.query(Clause).filter(Clause.document_id == updated_doc.id).all()
    assert len(clauses) > 0
    db.close()


def test_get_document_status_endpoint():
    """
    Test GET /api/v1/documents/{id}/status endpoint.
    """
    client = TestClient(app)
    db = TestingSessionLocal()

    doc = Document(
        id=uuid.uuid4(),
        filename="status_test.pdf",
        user_id=USER_ID,
        status="processing"
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)
    db.close()

    # Query status endpoint
    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["progress"] == 50
    assert data["document_id"] == doc_id
    assert data["error"] is None

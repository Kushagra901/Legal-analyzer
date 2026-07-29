# test_review_queue.py
"""
Unit Tests for Clause Review Queue Persistence.
Tests creating, updating, and fetching clause review decisions and audit log generation.
"""
import os
import sys
import uuid

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import AuditLog, Clause, Document, Organization, User

# Setup in-memory SQLite database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user(request: Request, db: Session = Depends(override_get_db)):
    user = db.query(User).filter(User.id == TEST_USER_ID).first()
    if not user:
        user = User(
            id=TEST_USER_ID,
            email="attorney@example.com",
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    old_get_db = app.dependency_overrides.get(get_db)
    old_get_user = app.dependency_overrides.get(get_current_user)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    org = Organization(id=TEST_USER_ID, name="Test Law Firm", plan="free")
    user = User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="attorney@example.com", role="user")
    db.add(org)
    db.add(user)
    db.commit()
    db.close()

    yield

    if old_get_db is not None:
        app.dependency_overrides[get_db] = old_get_db
    else:
        app.dependency_overrides.pop(get_db, None)

    if old_get_user is not None:
        app.dependency_overrides[get_current_user] = old_get_user
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_clause_review_create_and_get():
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, user_id=TEST_USER_ID, filename="contract.pdf", status="completed")
    db.add(doc)

    clause_id = uuid.uuid4()
    clause = Clause(id=clause_id, document_id=doc_id, clause_type="Limitation of Liability", clause_text="Uncapped liability clause text.")
    db.add(clause)
    db.commit()
    db.close()

    # 1. Submit review decision "approved"
    resp = client.post(
        f"/api/v1/documents/{doc_id}/clauses/{clause_id}/review",
        json={"decision": "approved", "note": "Acceptable under enterprise risk policy."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "approved"
    assert data["note"] == "Acceptable under enterprise risk policy."
    assert data["clause_id"] == str(clause_id)
    assert data["document_id"] == str(doc_id)

    # 2. Fetch document reviews
    get_resp = client.get(f"/api/v1/documents/{doc_id}/reviews")
    assert get_resp.status_code == 200
    reviews = get_resp.json()
    assert len(reviews) == 1
    assert reviews[0]["decision"] == "approved"
    assert reviews[0]["note"] == "Acceptable under enterprise risk policy."

    # 3. Verify audit log entry written
    db_session = TestingSessionLocal()
    logs = db_session.query(AuditLog).filter(AuditLog.document_id == doc_id).all()
    assert len(logs) >= 1
    assert "set to 'approved'" in logs[0].action
    db_session.close()


def test_clause_review_upsert_update():
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    doc = Document(id=doc_id, user_id=TEST_USER_ID, filename="nda.pdf", status="completed")
    db.add(doc)

    clause_id = uuid.uuid4()
    clause = Clause(id=clause_id, document_id=doc_id, clause_type="Indemnification", clause_text="Broad indemnification clause text.")
    db.add(clause)
    db.commit()
    db.close()

    # 1. Initial decision: approved
    client.post(
        f"/api/v1/documents/{doc_id}/clauses/{clause_id}/review",
        json={"decision": "approved", "note": "Initial pass okay."}
    )

    # 2. Re-review decision: redline_flagged
    resp = client.post(
        f"/api/v1/documents/{doc_id}/clauses/{clause_id}/review",
        json={"decision": "redline_flagged", "note": "Re-evaluated: requires cap."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "redline_flagged"
    assert data["note"] == "Re-evaluated: requires cap."

    # 3. Verify only 1 review record exists for the clause
    get_resp = client.get(f"/api/v1/documents/{doc_id}/reviews")
    reviews = get_resp.json()
    assert len(reviews) == 1
    assert reviews[0]["decision"] == "redline_flagged"

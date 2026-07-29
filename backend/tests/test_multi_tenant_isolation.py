"""
Unit tests for multi-tenant data isolation and ownership access control.
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
from app.models import Document, Organization, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

USER_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

current_test_user_id = USER_1_ID


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    db = TestingSessionLocal()
    org = db.query(Organization).filter(Organization.id == ORG_ID).first()
    if not org:
        org = Organization(id=ORG_ID, name="Tenant Org", plan="free")
        db.add(org)
        db.commit()

    user = db.query(User).filter(User.id == current_test_user_id).first()
    if not user:
        user = User(
            id=current_test_user_id,
            org_id=ORG_ID,
            email=f"user-{current_test_user_id}@tenant.com",
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user


@pytest.fixture(autouse=True)
def setup_multi_tenant_overrides():
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


def test_user_cannot_access_other_user_document():
    global current_test_user_id
    client = TestClient(app)
    db = TestingSessionLocal()

    doc_1 = Document(
        id=uuid.uuid4(),
        filename="user1_contract.pdf",
        user_id=USER_1_ID,
        status="completed",
        summary="User 1 Summary",
        safety_score=90,
        risk_level="LOW"
    )
    db.add(doc_1)
    db.commit()
    doc_1_id = str(doc_1.id)
    db.close()

    # User 1 can access their document
    current_test_user_id = USER_1_ID
    res_1 = client.get(f"/api/v1/documents/{doc_1_id}")
    assert res_1.status_code == 200

    # User 2 tries to access User 1's document -> 403 Forbidden
    current_test_user_id = USER_2_ID
    res_2 = client.get(f"/api/v1/documents/{doc_1_id}")
    assert res_2.status_code == 403
    assert "Access denied" in res_2.json()["detail"]


def test_user_cannot_delete_other_user_document():
    global current_test_user_id
    client = TestClient(app)
    db = TestingSessionLocal()

    doc = Document(
        id=uuid.uuid4(),
        filename="user1_secret.pdf",
        user_id=USER_1_ID,
        status="completed"
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)
    db.close()

    # User 2 attempts to delete User 1's document -> 403 Forbidden
    current_test_user_id = USER_2_ID
    res = client.delete(f"/api/v1/documents/{doc_id}")
    assert res.status_code == 403

    # User 1 deletes their document -> 200 OK
    current_test_user_id = USER_1_ID
    res_delete = client.delete(f"/api/v1/documents/{doc_id}")
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "deleted"


def test_list_documents_filters_by_user_id():
    global current_test_user_id
    client = TestClient(app)
    db = TestingSessionLocal()

    doc_u1 = Document(filename="u1_doc.pdf", user_id=USER_1_ID, status="completed")
    doc_u2 = Document(filename="u2_doc.pdf", user_id=USER_2_ID, status="completed")
    db.add(doc_u1)
    db.add(doc_u2)
    db.commit()
    db.close()

    # User 1 list only returns u1_doc.pdf
    current_test_user_id = USER_1_ID
    res_1 = client.get("/api/v1/documents")
    assert res_1.status_code == 200
    docs_1 = res_1.json()
    assert len(docs_1) == 1
    assert docs_1[0]["filename"] == "u1_doc.pdf"

    # User 2 list only returns u2_doc.pdf
    current_test_user_id = USER_2_ID
    res_2 = client.get("/api/v1/documents")
    assert res_2.status_code == 200
    docs_2 = res_2.json()
    assert len(docs_2) == 1
    assert docs_2[0]["filename"] == "u2_doc.pdf"

"""
Unit tests for eager loading of Clause.risk_flags relationship.
Validates PERF-DB-001-RELATIONSHIP-EAGER-LOAD requirements.
"""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import Clause, Document, RiskFlag, User

# In-memory SQLite for testing eager loading
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)

TEST_USER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_user():
    return User(id=TEST_USER_ID, org_id=TEST_USER_ID, email="test@example.com", role="user")


def test_orm_relationship_configuration():
    """Verify that Clause and RiskFlag ORM relationships and cascade are configured."""
    from sqlalchemy.inspection import inspect

    clause_mapper = inspect(Clause)
    assert "risk_flags" in clause_mapper.relationships
    rf_rel = clause_mapper.relationships["risk_flags"]
    assert rf_rel.back_populates == "clause"
    assert rf_rel.lazy == "selectin"
    assert "delete-orphan" in rf_rel.cascade

    risk_flag_mapper = inspect(RiskFlag)
    assert "clause" in risk_flag_mapper.relationships
    clause_rel = risk_flag_mapper.relationships["clause"]
    assert clause_rel.back_populates == "risk_flags"


def test_cascade_delete_relationship():
    """Verify that deleting a clause cascades to its risk flags."""
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    clause_id = uuid.uuid4()

    clause = Clause(
        id=clause_id,
        document_id=doc_id,
        clause_type="Confidentiality",
        clause_text="Sample text",
        category="General",
    )
    db.add(clause)
    db.flush()

    flag = RiskFlag(
        id=uuid.uuid4(),
        clause_id=clause_id,
        severity="HIGH",
        explanation="Overly broad clause",
    )
    db.add(flag)
    db.commit()

    # Verify both exist
    assert db.query(RiskFlag).filter(RiskFlag.clause_id == clause_id).count() == 1

    # Delete clause and verify risk flag is cascade deleted
    db.delete(clause)
    db.commit()
    assert db.query(RiskFlag).filter(RiskFlag.clause_id == clause_id).count() == 0
    db.close()


def test_get_document_eliminates_n_plus_one_queries():
    """
    Verify that get_document does not execute individual queries for each clause's risk flags.
    With 10 clauses, the queries to risk_flags should be 0 or 1 (eager loaded), not 10.
    """
    db = TestingSessionLocal()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=TEST_USER_ID,
        filename="multiclause_test.pdf",
        status="completed",
        uploaded_at=datetime.now(UTC),
    )
    db.add(doc)

    for i in range(10):
        c_id = uuid.uuid4()
        c = Clause(
            id=c_id,
            document_id=doc_id,
            clause_type=f"Clause_{i}",
            clause_text=f"Text for clause {i}",
            category="General",
        )
        db.add(c)
        db.flush()

        rf = RiskFlag(
            id=uuid.uuid4(),
            clause_id=c_id,
            severity="MEDIUM" if i % 2 == 0 else "LOW",
            explanation=f"Explanation for clause {i}",
        )
        db.add(rf)

    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_user

    executed_statements = []

    def statement_listener(conn, cursor, statement, parameters, context, executemany):
        executed_statements.append(statement)

    event.listen(engine, "before_cursor_execute", statement_listener)
    try:
        response = client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()

        clauses = data["analysis"]["clauses"]
        assert len(clauses) == 10
        for i, c in enumerate(clauses):
            assert c["type"] == f"Clause_{i}"
            expected_severity = "MEDIUM" if i % 2 == 0 else "LOW"
            assert c["severity"] == expected_severity

        # Count how many individual SELECT queries targeted risk_flags
        # In N+1, there would be 10 queries like: SELECT ... FROM risk_flags WHERE risk_flags.clause_id = ?
        individual_rf_queries = [
            stmt for stmt in executed_statements
            if "FROM risk_flags WHERE risk_flags.clause_id" in stmt or
               ("FROM risk_flags" in stmt and "JOIN" not in stmt and "IN (" not in stmt)
        ]
        assert len(individual_rf_queries) == 0, (
            f"Detected {len(individual_rf_queries)} N+1 queries for risk_flags: {individual_rf_queries}"
        )
    finally:
        event.remove(engine, "before_cursor_execute", statement_listener)
        app.dependency_overrides.clear()

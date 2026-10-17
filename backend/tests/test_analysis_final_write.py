"""
Tests for document analysis final-write normalization and error sanitization.

Verifies:
1. Normalization of dictionary summary ({'key_terms': [...], 'risk_posture': '...'})
   into risk_posture string and separate key_terms field, ensuring all document
   fields (status, safety_score, risk_level, parties, key_dates, missing_sections,
   document_overview, plain_english_summary) are properly saved.
2. Handling of simulated database exceptions on final write, ensuring status is set to
   'failed', generic message is stored in error_message, full traceback is logged, and
   no raw SQL or parameters leak into user-visible fields (doc.summary, doc.error_message, status endpoint).
"""

import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SqlSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import Document, ExtractedText, User
from app.services.llm_service import LLMService
from app.services.report_generator_service import ReportGeneratorService
from app.workers.tasks import execute_document_analysis

# Isolated in-memory SQLite database for test execution
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


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
        email="test_attorney@example.com",
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


def test_final_write_with_dict_summary_saves_all_fields(monkeypatch):
    """
    Verify that when analysis returns summary as a dict ({'key_terms': [...], 'risk_posture': '...'}),
    the final write succeeds without error, saves risk_posture as a plain string in doc.summary,
    saves key_terms in doc.key_terms, and commits all other extracted fields.
    """
    monkeypatch.setattr("app.workers.tasks.SessionLocal", TestingSessionLocal)

    mock_analysis_result = {
        "summary": {
            "key_terms": ["Governing Law: California", "Indemnification Cap: $1,000,000", "Confidentiality: 3 years"],
            "risk_posture": "The contract presents a moderate risk posture due to uncapped mutual indemnification."
        },
        "document_overview": "Comprehensive Master Services Agreement governing software development services.",
        "plain_english_summary": "Alpha Corp agrees to provide custom engineering services to Beta LLC.",
        "parties": ["Alpha Technologies Inc.", "Beta Enterprise LLC"],
        "key_dates": {
            "effective_date": "2026-05-01",
            "expiration_date": "2028-05-01",
            "notice_period": "60 days"
        },
        "missing_sections": ["Force Majeure", "Data Protection Addendum (GDPR)"],
        "safety_score": 80,
        "risk_level": "MEDIUM",
        "clauses": [
            {
                "clause_type": "Indemnification",
                "clause_text": "Party A shall indemnify Party B from all third-party intellectual property claims.",
                "severity": "MEDIUM",
                "explanation": "Standard IP indemnity with potential exposure.",
                "category": "Liability & Risk",
                "confidence_score": 0.95
            }
        ],
        "citations": [
            {"source": "Cal. Civ. Code § 1668", "citation": "California Civil Code on contract limits"}
        ],
        "recommendations": ["Cap indemnity liability to 12 months of fees paid."]
    }

    # Mock LLMService to return the dict-summary analysis result
    monkeypatch.setattr(
        "app.services.llm_service.LLMService.analyze_contract",
        lambda self, text: mock_analysis_result
    )

    # Mock embedding chunking to run cleanly in memory
    monkeypatch.setattr(
        "app.services.embedding_service.EmbeddingService.chunk_and_embed_document",
        lambda self, doc_id, text, db: None
    )

    db = TestingSessionLocal()
    doc = Document(
        id=uuid.uuid4(),
        filename="master_services_agreement.pdf",
        user_id=USER_ID,
        status="processing"
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="This Master Services Agreement is entered into by Alpha Technologies Inc. and Beta Enterprise LLC.",
        method="native"
    )
    db.add(extracted)
    db.commit()
    db.close()

    # Run the background analysis task
    execute_document_analysis(doc_id)

    # Inspect database state
    db = TestingSessionLocal()
    updated_doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()

    assert updated_doc is not None
    assert updated_doc.status == "completed"
    assert updated_doc.error_message is None

    # 1. Summary MUST be a plain string containing risk_posture, NOT a dict or stringified dict
    assert isinstance(updated_doc.summary, str)
    assert updated_doc.summary == "The contract presents a moderate risk posture due to uncapped mutual indemnification."
    assert not updated_doc.summary.startswith("{")

    # 2. Key terms must be stored in key_terms column
    assert updated_doc.key_terms == ["Governing Law: California", "Indemnification Cap: $1,000,000", "Confidentiality: 3 years"]

    # 3. All other contract intelligence fields must be saved successfully
    assert updated_doc.safety_score is not None
    assert updated_doc.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert updated_doc.parties == ["Alpha Technologies Inc.", "Beta Enterprise LLC"]
    assert updated_doc.key_dates == {
        "effective_date": "2026-05-01",
        "expiration_date": "2028-05-01",
        "notice_period": "60 days"
    }
    assert updated_doc.missing_sections == ["Force Majeure", "Data Protection Addendum (GDPR)"]
    assert updated_doc.document_overview == "Comprehensive Master Services Agreement governing software development services."
    assert updated_doc.plain_english_summary == "Alpha Corp agrees to provide custom engineering services to Beta LLC."

    # 4. Verify API response consumers receive normalized fields
    client = TestClient(app)
    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["status"] == "completed"
    assert doc_data["error_message"] is None
    assert doc_data["analysis"]["summary"] == "The contract presents a moderate risk posture due to uncapped mutual indemnification."
    assert doc_data["analysis"]["key_terms"] == ["Governing Law: California", "Indemnification Cap: $1,000,000", "Confidentiality: 3 years"]
    assert doc_data["analysis"]["document_overview"] == "Comprehensive Master Services Agreement governing software development services."
    assert doc_data["analysis"]["plain_english_summary"] == "Alpha Corp agrees to provide custom engineering services to Beta LLC."

    # 5. Verify ReportGeneratorService reader handles normalized fields seamlessly
    report_data = ReportGeneratorService.assemble_report_data(updated_doc, db)
    assert report_data["summary"] == "The contract presents a moderate risk posture due to uncapped mutual indemnification."
    assert report_data["document_overview"] == "Comprehensive Master Services Agreement governing software development services."
    assert report_data["plain_english_summary"] == "Alpha Corp agrees to provide custom engineering services to Beta LLC."
    assert report_data["key_terms"] == ["Governing Law: California", "Indemnification Cap: $1,000,000", "Confidentiality: 3 years"]

    db.close()


def test_simulated_db_error_sets_failed_status_without_sql_leak(monkeypatch, caplog):
    """
    Verify that when a database error (simulating psycopg2.ProgrammingError or similar) occurs
    during document analysis write, the document status is set to 'failed', the full traceback
    is recorded in server logs, and a generic error message is stored in doc.error_message without
    leaking any raw SQL, database parameters, or exception details into user-visible fields.
    """
    monkeypatch.setattr("app.workers.tasks.SessionLocal", TestingSessionLocal)

    sql_error_payload = (
        'psycopg2.ProgrammingError: syntax error at or near "SELECT secret_password_hash FROM users WHERE id=\'user-999\'"\n'
        'LINE 1: UPDATE documents SET summary={\'key_terms\': [\'internal_token_xyz\']} WHERE id = \'doc-123\';\n'
        '[SQL: UPDATE documents SET summary=:summary WHERE documents.id = :id]\n'
        '[parameters: {\'summary\': {\'key_terms\': [\'internal_token_xyz\']}, \'id\': \'secret-uuid\'}]'
    )

    # Mock LLMService to simulate analysis output
    monkeypatch.setattr(
        "app.services.llm_service.LLMService.analyze_contract",
        lambda self, text: {
            "summary": {"key_terms": ["Confidential"], "risk_posture": "LOW"},
            "clauses": [],
            "citations": [],
            "recommendations": []
        }
    )

    db = TestingSessionLocal()
    doc = Document(
        id=uuid.uuid4(),
        filename="classified_contract.pdf",
        user_id=USER_ID,
        status="processing",
        summary=None,
        error_message=None
    )
    db.add(doc)
    db.commit()
    doc_id = str(doc.id)

    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc.id,
        content="Confidential proprietary agreement.",
        method="native"
    )
    db.add(extracted)
    db.commit()
    db.close()

    # Track commit count to fail on the document update commit, but allow the failure status commit
    real_commit = SqlSession.commit
    commit_calls = {"count": 0}

    def flaky_commit(session_self):
        commit_calls["count"] += 1
        # Fail the update commit (commit call #2)
        if commit_calls["count"] == 2:
            raise Exception(sql_error_payload)
        return real_commit(session_self)

    monkeypatch.setattr("sqlalchemy.orm.Session.commit", flaky_commit)

    with caplog.at_level(logging.ERROR):
        execute_document_analysis(doc_id)

    # 1. Verify database state after simulated failure
    db = TestingSessionLocal()
    failed_doc = db.query(Document).filter(Document.id == uuid.UUID(doc_id)).first()

    assert failed_doc is not None
    assert failed_doc.status == "failed"

    # 2. Verify doc.summary DOES NOT contain exception text or SQL
    assert failed_doc.summary != f"Analysis failure: {sql_error_payload}"
    assert failed_doc.summary is None or "SELECT" not in failed_doc.summary
    assert "psycopg2" not in (failed_doc.summary or "")
    assert "secret_password_hash" not in (failed_doc.summary or "")
    assert "internal_token_xyz" not in (failed_doc.summary or "")

    # 3. Verify doc.error_message has a clean generic message without SQL or parameters
    assert failed_doc.error_message == "Document analysis failed. Please retry."
    assert "SELECT" not in failed_doc.error_message
    assert "secret_password_hash" not in failed_doc.error_message
    assert "internal_token_xyz" not in failed_doc.error_message
    assert "SQL" not in failed_doc.error_message
    assert "psycopg2" not in failed_doc.error_message

    # 4. Verify user-facing status endpoint does NOT leak SQL or exception text
    client = TestClient(app)
    status_resp = client.get(f"/api/v1/documents/{doc_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()

    assert status_data["status"] == "failed"
    assert status_data["error"] == "Document analysis failed. Please retry."
    assert "SELECT" not in (status_data["error"] or "")
    assert "secret_password_hash" not in (status_data["error"] or "")
    assert "internal_token_xyz" not in (status_data["error"] or "")
    assert "psycopg2" not in (status_data["error"] or "")
    assert "SQL" not in (status_data["error"] or "")

    # 5. Verify server log recorded the full traceback
    log_text = caplog.text
    assert "Error in analyze_document_task for" in log_text
    assert "psycopg2.ProgrammingError" in log_text

    db.close()


def test_llm_service_normalizes_dict_summary_in_calibrate():
    """
    Verify that LLMService._validate_and_calibrate_scores normalizes a dict summary
    to the risk_posture string and extracts key_terms.
    """
    service = LLMService()
    raw_payload = {
        "summary": {
            "key_terms": ["NDA", "2-year term", "California choice of law"],
            "risk_posture": "Low risk mutual agreement with standard carveouts."
        },
        "safety_score": 90,
        "risk_level": "LOW",
        "clauses": [],
        "citations": [],
        "recommendations": []
    }

    calibrated = service._validate_and_calibrate_scores(raw_payload, "Mutual NDA agreement.")
    assert calibrated["summary"] == "Low risk mutual agreement with standard carveouts."
    assert isinstance(calibrated["summary"], str)
    assert calibrated["key_terms"] == ["NDA", "2-year term", "California choice of law"]

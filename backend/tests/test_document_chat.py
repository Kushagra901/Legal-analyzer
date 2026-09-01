# test_document_chat.py
"""
Unit and integration tests for Grounded Document Chat Service and Endpoints.
Tests prompt grounding, citation resolution, chat history persistence, and audit logging.
"""
import json
import os
import sys
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Depends, Request

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    ChatMessage,
    Clause,
    Document,
    DocumentChunk,
    ExtractedText,
    Organization,
    User,
)
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.ocr_service import OCRService

# SQLite in-memory setup for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user(request: Request, db=Depends(override_get_db)):
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    org = db.query(Organization).filter(Organization.id == test_uuid).first()
    if not org:
        org = Organization(id=test_uuid, name="Test Org", plan="free")
        db.add(org)
        db.commit()
    user = db.query(User).filter(User.id == test_uuid).first()
    if not user:
        user = User(id=test_uuid, org_id=test_uuid, email="test@example.com", role="user")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.query(ChatMessage).delete()
    db.query(DocumentChunk).delete()
    db.query(ExtractedText).delete()
    db.query(Clause).delete()
    db.query(Document).delete()
    db.commit()
    db.close()
    yield


# --- Unit Tests for ChatService ---

MOCK_CHAT_SUCCESS = {
    "answer": "Under Section 8.2, either party may terminate with 30 days written notice.",
    "citations": [
        {
            "clause_type": "Termination",
            "snippet": "Either party may terminate this agreement upon 30 days written notice."
        }
    ],
    "confidence": "HIGH",
    "disclaimer": "This AI response assists document review and is not legal advice."
}


def test_chat_service_grounded_answer():
    """Test ChatService successfully generates grounded answer with citations."""
    service = ChatService()

    clauses = [
        {"clause_type": "Termination", "clause_text": "Either party may terminate this agreement upon 30 days written notice."},
        {"clause_type": "Limitation of Liability", "clause_text": "Total liability shall not exceed the fees paid in the past 12 months."}
    ]

    with patch.object(service.llm_service, "_call_gemini", return_value=MOCK_CHAT_SUCCESS):
        with patch.object(service.llm_service, "gemini_api_key", "mock_key"):
            result = service.answer_question("How can I terminate?", clauses, {"filename": "contract.pdf"})
            assert result["confidence"] == "HIGH"
            assert "Section 8.2" in result["answer"]
            assert len(result["citations"]) == 1
            assert result["citations"][0]["clause_type"] == "Termination"


def test_chat_service_keyword_search():
    """Test keyword matching for relevant clause retrieval."""
    service = ChatService()
    clauses = [
        {"clause_type": "Indemnity", "clause_text": "Party A will indemnify Party B for losses."},
        {"clause_type": "Governing Law", "clause_text": "This contract is governed by Delaware law."},
        {"clause_type": "Payment", "clause_text": "Invoices are payable within 30 days of receipt."}
    ]

    results = service._search_clauses_by_keywords("What is the governing law?", clauses)
    assert len(results) >= 1
    assert results[0]["clause_type"] == "Governing Law"


def test_chat_endpoints_full_lifecycle():
    """Test POST /chat and GET /chat/history endpoints."""
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename="lease.pdf",
        status="completed"
    )
    db.add(doc)
    db.commit()

    clause = Clause(
        id=uuid.uuid4(),
        document_id=doc_id,
        clause_type="Termination",
        clause_text="Tenant may terminate upon 60 days notice."
    )
    db.add(clause)
    db.commit()
    db.close()

    with patch.object(ChatService, "answer_question_with_chunks", return_value=MOCK_CHAT_SUCCESS):
        # 1. Send chat message
        chat_req = {
            "query": "Can tenant terminate early?",
            "conversation_id": None
        }
        res = client.post(f"/api/v1/documents/{doc_id}/chat", json=chat_req)
        assert res.status_code == 200
        data = res.json()
        assert "Section 8.2" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["confidence"] == "HIGH"

        # 2. Get chat history
        history_res = client.get(f"/api/v1/documents/{doc_id}/chat/history")
        assert history_res.status_code == 200
        history_data = history_res.json()
        assert len(history_data) == 2  # user message + assistant message
        assert history_data[0]["role"] == "user"
        assert history_data[0]["content"] == "Can tenant terminate early?"
        assert history_data[1]["role"] == "assistant"
        assert "Section 8.2" in history_data[1]["content"]


def test_vector_chat_sample_nda_known_question():
    """
    Test vector chat against sample NDA with a question having a clear answer in the document text.
    Confirms grounded answer, citations, source chunks, and chat_messages persistence.
    """
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "test-documents",
        "sample-nda-test-document.pdf"
    )
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join("..", "test-documents", "sample-nda-test-document.pdf")

    ocr = OCRService()
    extracted_text, _, _ = ocr.process_document(pdf_path)

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename="sample-nda-test-document.pdf",
        status="completed"
    )
    db.add(doc)

    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=extracted_text,
        method="native"
    )
    db.add(ext)
    db.commit()

    # Pre-chunk document
    embedding_service = EmbeddingService()
    embedding_service.chunk_and_embed_document(doc_id, extracted_text, db)
    db.close()

    # Ask known question: Who are the parties to this agreement?
    payload = {"question": "Who are the parties to this agreement?"}
    res = client.post(f"/api/v1/documents/{doc_id}/chat", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()

    assert "answer" in data
    assert "source_chunks" in data
    assert len(data["source_chunks"]) > 0
    assert len(data["source_chunks"]) <= 5
    for sc in data["source_chunks"]:
        assert sc["chunk_text"]

    # Verify parties mentioned or grounded answer returned
    answer_lower = data["answer"].lower()
    assert "acme" in answer_lower or "jane doe" in answer_lower or "disclosing" in answer_lower or "receiving" in answer_lower

    # Verify chat_messages persisted in database
    db = TestingSessionLocal()
    msgs = db.query(ChatMessage).filter(ChatMessage.document_id == doc_id).order_by(ChatMessage.created_at.asc()).all()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "Who are the parties to this agreement?"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == data["answer"]
    db.close()


def test_vector_chat_sample_nda_unknown_question():
    """
    Test vector chat against sample NDA with a question having NO answer in the document text.
    Confirms assistant explicitly responds 'I can't find that in this document' and does not hallucinate.
    """
    db = TestingSessionLocal()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    pdf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "test-documents",
        "sample-nda-test-document.pdf"
    )
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join("..", "test-documents", "sample-nda-test-document.pdf")

    ocr = OCRService()
    extracted_text, _, _ = ocr.process_document(pdf_path)

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename="sample-nda-test-document.pdf",
        status="completed"
    )
    db.add(doc)

    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=extracted_text,
        method="native"
    )
    db.add(ext)
    db.commit()

    embedding_service = EmbeddingService()
    embedding_service.chunk_and_embed_document(doc_id, extracted_text, db)
    db.close()

    # Ask unanswerable question
    payload = {"question": "What is the monthly subscription fee for the SaaS software product?"}
    res = client.post(f"/api/v1/documents/{doc_id}/chat", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()

    assert "answer" in data
    # Confirm it explicitly states "I can't find that in this document"
    assert "can't find that in this document" in data["answer"].lower() or "cannot find that in this document" in data["answer"].lower()
    assert len(data["source_chunks"]) > 0

    # Verify chat_messages persisted
    db = TestingSessionLocal()
    msgs = db.query(ChatMessage).filter(ChatMessage.document_id == doc_id).order_by(ChatMessage.created_at.asc()).all()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
    assert "can't find that" in msgs[1].content.lower() or "cannot find that" in msgs[1].content.lower()
    db.close()


def test_vector_chat_document_isolation_rls():
    """
    Test vector chat respects user ownership / RLS boundary and does not allow
    accessing another user's document chunks.
    """
    db = TestingSessionLocal()
    other_user_id = uuid.uuid4()
    other_user = User(
        id=other_user_id,
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        role="user"
    )
    db.add(other_user)

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=other_user_id,
        filename="confidential_memo.pdf",
        status="completed"
    )
    db.add(doc)
    db.commit()
    db.close()

    payload = {"question": "What are the terms?"}
    res = client.post(f"/api/v1/documents/{doc_id}/chat", json=payload)
    assert res.status_code in (403, 404)

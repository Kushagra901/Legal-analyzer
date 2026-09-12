"""
test_embedding_and_chunks.py
Unit and integration tests for document chunking, 768-dimensional Gemini embeddings,
and document_chunks + chat_messages database tables.
"""
import os
import sys
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.models.database_models import (
    ChatMessage,
    Document,
    DocumentChunk,
    User,
)
from app.services.embedding_service import EmbeddingService

# Setup in-memory SQLite database for test execution
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"test_embed_{uuid.uuid4().hex[:8]}@example.com",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_document(db_session, sample_user):
    doc = Document(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        filename="test_contract.pdf",
        status="completed"
    )
    db_session.add(doc)
    db_session.commit()
    return doc


def test_chunk_text_algorithm():
    """
    Test chunk_text correctly splits text into ~800-char overlapping chunks.
    """
    service = EmbeddingService()

    # 1. Short text (< 800 chars)
    short_text = "This is a brief non-disclosure agreement between Party A and Party B."
    chunks_short = service.chunk_text(short_text, chunk_size=800, overlap=150)
    assert len(chunks_short) == 1
    assert chunks_short[0]["chunk_index"] == 0
    assert chunks_short[0]["chunk_text"] == short_text

    # 2. Empty text
    assert service.chunk_text("") == []
    assert service.chunk_text("   \n\t  ") == []

    # 3. Long text (> 2500 chars)
    paragraph = (
        "1. Confidentiality Obligations. The Receiving Party agrees to maintain the confidential nature "
        "of all proprietary technical and commercial information disclosed by the Disclosing Party. "
        "The standard of care shall be no less than a reasonable degree of care applied to own trade secrets. "
    )
    long_text = "\n\n".join([f"Section {i}.\n{paragraph}" for i in range(1, 12)])
    assert len(long_text) > 2500

    chunks = service.chunk_text(long_text, chunk_size=800, overlap=150)
    assert len(chunks) >= 3

    # Check indices are sequential
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
        assert len(c["chunk_text"]) > 0
        # Most chunks should be <= 850 chars
        assert len(c["chunk_text"]) <= 950


def test_generate_embedding_dimension_and_values():
    """
    Test generate_embedding produces exact 768-dimensional float vectors.
    """
    service = EmbeddingService()
    text = "This agreement governs the disclosure of confidential trade secret information."

    emb = service.generate_embedding(text)
    assert isinstance(emb, list)
    assert len(emb) == 768
    assert all(isinstance(v, (float, int)) for v in emb)

    # Test fallback embedding normalization
    fallback_emb = service._generate_fallback_embedding(text)
    assert len(fallback_emb) == 768
    # Norm should be close to 1.0
    norm_sq = sum(x * x for x in fallback_emb)
    assert 0.95 <= norm_sq <= 1.05


def test_chunk_and_embed_document_db_persistence(db_session, sample_document):
    """
    Test chunking and embedding storage in document_chunks table.
    """
    service = EmbeddingService()
    sample_text = (
        "FRANCHISE AGREEMENT\n\n"
        "This Franchise Agreement is entered into by Sundara Foods Franchising Pvt. Ltd. and Arjun Malhotra.\n"
        + ("Operational guidelines and supply chain requirements for food outlet.\n" * 20)
    )

    # Execute chunk and embed
    chunks = service.chunk_and_embed_document(
        document_id=sample_document.id,
        extracted_text=sample_text,
        db=db_session,
        chunk_size=400,
        overlap=80
    )

    assert len(chunks) > 1

    # Verify directly from database
    stored_chunks = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == sample_document.id
    ).order_by(DocumentChunk.chunk_index.asc()).all()

    assert len(stored_chunks) == len(chunks)
    for idx, sc in enumerate(stored_chunks):
        assert sc.chunk_index == idx
        assert sc.document_id == sample_document.id
        assert len(sc.chunk_text) > 0
        assert sc.embedding is not None

    # Test idempotency (re-running replaces previous chunks)
    new_chunks = service.chunk_and_embed_document(
        document_id=sample_document.id,
        extracted_text="Short updated text.",
        db=db_session
    )
    assert len(new_chunks) == 1
    updated_stored = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == sample_document.id
    ).all()
    assert len(updated_stored) == 1
    assert updated_stored[0].chunk_text == "Short updated text."


def test_chat_messages_db_persistence(db_session, sample_document, sample_user):
    """
    Test storing and retrieving records in chat_messages table.
    """
    conv_id = uuid.uuid4()

    # Add user message
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        user_id=sample_user.id,
        conversation_id=conv_id,
        role="user",
        content="What are the termination conditions?"
    )
    db_session.add(user_msg)

    # Add assistant response
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        user_id=sample_user.id,
        conversation_id=conv_id,
        role="assistant",
        content="The agreement may be terminated upon 90 days prior written notice.",
        citations=[{"source": "Termination Clause", "citation": "Section 4.1"}],
        confidence="HIGH"
    )
    db_session.add(assistant_msg)
    db_session.commit()

    # Query chat history
    history = db_session.query(ChatMessage).filter(
        ChatMessage.document_id == sample_document.id,
        ChatMessage.conversation_id == conv_id
    ).order_by(ChatMessage.created_at.asc()).all()

    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "What are the termination conditions?"
    assert history[1].role == "assistant"
    assert "90 days" in history[1].content
    assert history[1].confidence == "HIGH"

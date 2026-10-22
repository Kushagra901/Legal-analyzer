"""
test_embedding_and_chunks.py
Unit and integration tests for document chunking, 768-dimensional Gemini embeddings,
and document_chunks + chat_messages database tables.
"""
import os
import sys
import uuid
from unittest.mock import MagicMock, call, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.models.database_models import (
    ChatMessage,
    Clause,
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


def test_clause_vector_type_sqlite_persistence(db_session, sample_document):
    """
    Ensure Clause embedding with VectorType(768) persists and serializes cleanly on SQLite.
    """
    dummy_vector = [0.123] * 768
    clause = Clause(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        clause_type="INDEMNIFICATION",
        clause_text="Party A shall indemnify Party B...",
        embedding=dummy_vector,
        confidence_score=0.95,
        category="Risk",
    )
    db_session.add(clause)
    db_session.commit()

    retrieved = db_session.query(Clause).filter(Clause.id == clause.id).first()
    assert retrieved is not None
    assert isinstance(retrieved.embedding, list)
    assert len(retrieved.embedding) == 768
    assert retrieved.embedding[0] == pytest.approx(0.123)


def test_document_chunk_unique_constraint_enforcement(db_session, sample_document):
    """
    Ensure UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index')
    prevents duplicate chunk indexes for the same document.
    """
    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        chunk_index=0,
        chunk_text="First chunk text",
        embedding=[0.05] * 768,
    )
    db_session.add(chunk1)
    db_session.commit()

    chunk_duplicate = DocumentChunk(
        id=uuid.uuid4(),
        document_id=sample_document.id,
        chunk_index=0,
        chunk_text="Duplicate chunk index text",
        embedding=[0.05] * 768,
    )
    db_session.add(chunk_duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_batch_embedding_empty_and_edge_cases():
    """
    Edge case tests: empty list, None, empty string, and whitespace.
    Ensures safe handling without unhandled exceptions or index errors.
    """
    service = EmbeddingService(api_key="test-api-key")

    # 1. Empty list
    assert service.generate_embeddings_batch([]) == []

    # 2. None, empty string, whitespace elements
    edge_cases = ["", "   \n\t ", None]
    results = service.generate_embeddings_batch(edge_cases, delay_between_batches=0.0)
    assert len(results) == 3
    for emb in results:
        assert isinstance(emb, list)
        assert len(emb) == 768
        assert all(isinstance(v, float) for v in emb)

    # 3. None and empty text in chunk_text
    assert service.chunk_text(None) == []
    assert service.chunk_text("") == []
    assert service.chunk_text("   ") == []

    # 4. None and empty text in generate_embedding
    single_none = service.generate_embedding(None)
    assert len(single_none) == 768
    single_empty = service.generate_embedding("")
    assert len(single_empty) == 768


def test_batch_embedding_groups_of_5_and_pacing():
    """
    Verify chunks are grouped into batches of 5 with pacing delay applied between batches.
    """
    service = EmbeddingService(batch_size=5, batch_delay=0.5, api_key="")
    texts = [f"Clause paragraph chunk {i} with distinct legal provisions." for i in range(12)]

    with patch("time.sleep") as mock_sleep:
        embeddings = service.generate_embeddings_batch(
            texts,
            batch_size=5,
            delay_between_batches=0.5
        )

        assert len(embeddings) == 12
        # For 12 items with batch_size 5: batch 0 (5), batch 1 (5), batch 2 (2) -> 2 sleeps
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(0.5), call(0.5)])


def test_gemini_batch_api_success_with_batch_embed_contents():
    """
    Test successful execution of Gemini batchEmbedContents endpoint with valid response.
    """
    service = EmbeddingService(api_key="valid-mock-key")
    dummy_vec = [0.0123] * 768

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embeddings": [
            {"values": dummy_vec},
            {"values": dummy_vec},
            {"values": dummy_vec},
        ]
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        texts = ["Text chunk 1", "Text chunk 2", "Text chunk 3"]
        results = service._call_gemini_batch_api(texts)

        assert len(results) == 3
        assert all(len(v) == 768 for v in results)
        assert results[0][0] == pytest.approx(0.0123)

        # Verify POST payload format
        post_args = mock_client.post.call_args
        assert ":batchEmbedContents" in post_args[0][0]
        payload = post_args[1]["json"]
        assert "requests" in payload
        assert len(payload["requests"]) == 3
        assert payload["requests"][0]["outputDimensionality"] == 768


def test_gemini_429_retry_with_exponential_backoff():
    """
    Simulate HTTP 429 Too Many Requests error on initial attempt,
    verifying exponential backoff retry succeeds when the subsequent attempt passes.
    """
    service = EmbeddingService(api_key="valid-mock-key")
    dummy_vec = [0.0456] * 768

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents")
    resp_429 = httpx.Response(429, request=req, text="Rate limit exceeded. Too Many Requests.")
    resp_200 = httpx.Response(200, request=req, json={
        "embeddings": [{"values": dummy_vec}, {"values": dummy_vec}]
    })

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First attempt triggers 429
            return resp_429
        # Second attempt succeeds
        return resp_200

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = mock_post
        mock_client_cls.return_value = mock_client

        texts = ["Chunk 1", "Chunk 2"]
        # Use low multiplier for fast unit test execution
        results = service.generate_embeddings_batch(texts, batch_size=5, delay_between_batches=0.0)

        assert call_count == 2
        assert len(results) == 2
        assert len(results[0]) == 768
        assert results[0][0] == pytest.approx(0.0456)


def test_gemini_429_persistent_exhaustion_falls_back_gracefully():
    """
    Simulate persistent HTTP 429 where all retry attempts are exhausted.
    Ensures service does not crash or hang indefinitely, and falls back to deterministic embeddings.
    """
    service = EmbeddingService(api_key="valid-mock-key")

    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents")
    resp_429 = httpx.Response(429, request=req, text="Rate limit exceeded. Too Many Requests.")

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = resp_429
        mock_client_cls.return_value = mock_client

        texts = ["Section 1 Liability", "Section 2 Indemnification"]
        results = service.generate_embeddings_batch(texts, batch_size=5, delay_between_batches=0.0)

        # Must not raise, returns fallback embeddings
        assert len(results) == 2
        assert len(results[0]) == 768
        assert len(results[1]) == 768
        assert all(isinstance(x, float) for x in results[0])


def test_large_document_30_plus_chunks_simulation(db_session, sample_document):
    """
    Phase 2 requirement: Write a test simulating a large document (30+ chunks)
    to ensure it doesn't fail, hit rate limits unchecked, or hang indefinitely.
    """
    service = EmbeddingService(batch_size=5, batch_delay=0.0, api_key="")

    # Construct a document guaranteed to generate > 30 chunks (35+ chunks)
    clause_template = (
        "SECTION {num}. OPERATIONAL COVENANTS AND REGULATORY COMPLIANCE.\n"
        "The Franchisee covenants and agrees to strictly abide by the Standard Operating Procedures, "
        "food safety protocols under FSSAI regulations, audit inspection guidelines, brand standard manuals, "
        "and inventory procurement protocols established by Franchisor from time to time. "
        "Any material deviation or failure to maintain minimum safety hygiene scores exceeding 90% "
        "shall constitute an incurable immediate event of default under Article 12 of this Agreement.\n\n"
    )
    large_text = "MASTER COMMERCIAL FRANCHISE AGREEMENT\n\n" + "".join(
        clause_template.format(num=i) for i in range(1, 45)
    )

    # Verify text is large enough to produce > 30 chunks
    chunks_preview = service.chunk_text(large_text, chunk_size=600, overlap=100)
    assert len(chunks_preview) >= 30, f"Expected >= 30 chunks, got {len(chunks_preview)}"

    # Process through full chunk and embed pipeline
    saved_chunks = service.chunk_and_embed_document(
        document_id=sample_document.id,
        extracted_text=large_text,
        db=db_session,
        chunk_size=600,
        overlap=100,
        batch_size=5,
        delay_between_batches=0.0
    )

    assert len(saved_chunks) >= 30

    # Verify database persistence and sequential indices
    db_chunks = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == sample_document.id
    ).order_by(DocumentChunk.chunk_index.asc()).all()

    assert len(db_chunks) == len(saved_chunks)
    for idx, chunk in enumerate(db_chunks):
        assert chunk.chunk_index == idx
        assert chunk.document_id == sample_document.id
        assert len(chunk.chunk_text) > 0
        assert chunk.embedding is not None
        # Verify 768-dim float vector
        emb = chunk.embedding
        if isinstance(emb, list):
            assert len(emb) == 768
            assert all(isinstance(val, float) for val in emb)


def test_malformed_gemini_batch_response_padding_and_truncation():
    """
    Test that mismatched or malformed embedding vectors (e.g. 512 or 1024 floats, or missing items)
    are safely adjusted to 768 dimensions without raising errors.
    """
    service = EmbeddingService(api_key="valid-mock-key")

    short_vec = [0.1] * 512
    long_vec = [0.2] * 1024

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embeddings": [
            {"values": short_vec},
            {"values": long_vec},
            {"values": []},  # empty values
        ]
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        texts = ["Text A", "Text B", "Text C"]
        results = service.generate_embeddings_batch(texts, batch_size=5, delay_between_batches=0.0)

        assert len(results) == 3
        assert len(results[0]) == 768  # padded from 512
        assert len(results[1]) == 768  # truncated from 1024
        assert len(results[2]) == 768  # fallback substituted for empty


def test_chunk_and_embed_document_db_rollback_on_failure(db_session, sample_document):
    """
    Verify database rollback occurs if an error happens during chunk persistence,
    ensuring no half-persisted corrupted states remain.
    """
    service = EmbeddingService()
    test_text = "Sample contract text for rollback verification."

    with patch.object(service, "generate_embeddings_batch", side_effect=RuntimeError("Simulated batch failure")):
        with pytest.raises(RuntimeError) as exc_info:
            service.chunk_and_embed_document(
                document_id=sample_document.id,
                extracted_text=test_text,
                db=db_session
            )

        assert "Simulated batch failure" in str(exc_info.value)

    # Verify no chunks were left partially committed
    remaining = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == sample_document.id
    ).all()
    assert len(remaining) == 0


def test_gemini_429_fallback_to_ollama_when_available(monkeypatch):
    """
    Test that when Gemini encounters 429 errors, it falls back to Ollama
    if Ollama is configured and responding.
    """
    monkeypatch.setattr("app.core.config.settings.OLLAMA_BASE_URL", "http://localhost:11434")
    service = EmbeddingService(api_key="valid-mock-key")

    ollama_vec = [0.0789] * 768
    req = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents")
    resp_429 = httpx.Response(429, request=req, text="Rate limit exceeded.")
    resp_ollama = httpx.Response(200, request=httpx.Request("POST", "http://localhost:11434/api/embeddings"), json={"embedding": ollama_vec})

    def mock_post(url, *args, **kwargs):
        if "googleapis.com" in str(url):
            return resp_429
        if "11434" in str(url):
            return resp_ollama
        return resp_429

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = mock_post
        mock_client_cls.return_value = mock_client

        results = service.generate_embeddings_batch(["Sample clause for Ollama fallback"], batch_size=5, delay_between_batches=0.0)
        assert len(results) == 1
        assert len(results[0]) == 768
        assert results[0][0] == pytest.approx(0.0789)




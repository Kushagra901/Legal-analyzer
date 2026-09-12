"""
embedding_service.py
Service for document text chunking and 768-dimensional vector embedding generation
using Google Gemini embedding models and pgvector storage.
"""
import hashlib
import json
import logging
import math
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.database_models import DocumentChunk

logger = logging.getLogger(__name__)

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS_CODES
    if isinstance(exc, httpx.RequestError):
        return True
    return False


class EmbeddingService:
    """
    Service responsible for splitting document text into overlapping chunks
    and generating 768-dimensional embeddings via Gemini API or deterministic fallback.
    """

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.embedding_dim = 768
        self.primary_model = "models/gemini-embedding-001"
        self.fallback_model = "models/gemini-embedding-2"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
        """
        Split extracted document text into ~800-character overlapping chunks.
        Attempts to break chunks on paragraph or sentence boundaries when feasible.

        Returns:
            list[dict]: List of dictionaries with 'chunk_index' and 'chunk_text'.
        """
        if not text or not text.strip():
            return []

        text = text.strip()
        if len(text) <= chunk_size:
            return [{"chunk_index": 0, "chunk_text": text}]

        chunks = []
        start = 0
        text_len = len(text)
        chunk_idx = 0

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # If not at the end of the text, try to find a natural break near the end
            if end < text_len:
                # Look for paragraph break, then sentence break, then whitespace
                search_slice = text[start + chunk_size - overlap: end]
                split_offset = -1

                for delimiter in ["\n\n", "\n", ". ", "; ", ", ", " "]:
                    pos = search_slice.rfind(delimiter)
                    if pos != -1:
                        split_offset = (start + chunk_size - overlap) + pos + len(delimiter)
                        break

                if split_offset > start and split_offset <= end:
                    end = split_offset

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "chunk_text": chunk_content
                })
                chunk_idx += 1

            if end >= text_len:
                break

            # Move start forward with overlap
            next_start = end - overlap
            if next_start <= start:
                next_start = start + chunk_size - overlap
            start = max(next_start, start + 1)

        return chunks

    def _generate_fallback_embedding(self, text: str) -> list[float]:
        """
        Generate a deterministic, unit-normalized 768-dimensional float embedding vector
        from text when API key is not configured or in offline test environments.
        """
        hash_digest = hashlib.sha512(text.encode("utf-8")).digest()

        # Generate 768 floats from hashing rounds
        raw_vals = []
        seed = int.from_bytes(hash_digest[:8], "big")
        for i in range(self.embedding_dim):
            # Deterministic linear congruential pseudo-random generator
            seed = (1103515245 * seed + 12345 + i) & 0x7FFFFFFF
            val = (seed / 0x7FFFFFFF) * 2.0 - 1.0
            raw_vals.append(val)

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in raw_vals)) or 1.0
        return [float(round(x / norm, 6)) for x in raw_vals]

    @retry(
        retry=retry_if_exception(_is_retryable_exception),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=False
    )
    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a 768-dimensional vector embedding for a single text chunk via Gemini API.
        Falls back to a deterministic normalized vector if the API call fails or key is unset.
        """
        if not self.api_key:
            logger.info("No GEMINI_API_KEY configured; using fallback deterministic embedding.")
            return self._generate_fallback_embedding(text)

        url = f"{self.base_url}/{self.primary_model}:embedContent?key={self.api_key}"
        payload = {
            "model": self.primary_model,
            "content": {
                "parts": [{"text": text[:2000]}]  # Cap single chunk input safely
            },
            "outputDimensionality": self.embedding_dim
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                values = data.get("embedding", {}).get("values", [])
                if values and len(values) == self.embedding_dim:
                    return values
                elif values:
                    # Truncate or pad if dimension differs
                    if len(values) > self.embedding_dim:
                        return values[:self.embedding_dim]
                    else:
                        return values + [0.0] * (self.embedding_dim - len(values))
        except Exception as e:
            logger.warning(f"Gemini embedding API call failed: {e}. Utilizing fallback embedding.")

        return self._generate_fallback_embedding(text)

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of text chunks.
        """
        embeddings = []
        for item in texts:
            emb = self.generate_embedding(item)
            embeddings.append(emb)
        return embeddings

    def chunk_and_embed_document(
        self,
        document_id: uuid.UUID | str,
        extracted_text: str,
        db: Session,
        chunk_size: int = 800,
        overlap: int = 150
    ) -> list[DocumentChunk]:
        """
        Main pipeline function:
        1. Splits extracted document text into ~800-character overlapping chunks.
        2. Generates a 768-dim embedding for each chunk.
        3. Clears any previous chunks for document_id to maintain idempotency.
        4. Inserts new DocumentChunk records into document_chunks table and commits.

        Returns:
            list[DocumentChunk]: The created database records.
        """
        if isinstance(document_id, str):
            doc_uuid = uuid.UUID(document_id)
        else:
            doc_uuid = document_id

        chunks_data = self.chunk_text(extracted_text, chunk_size=chunk_size, overlap=overlap)
        if not chunks_data:
            logger.info(f"No text content found to chunk for document {doc_uuid}.")
            # Still delete old chunks if any
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete()
            db.commit()
            return []

        # Delete existing chunks for this document to ensure fresh storage
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete()
        db.flush()

        saved_chunks: list[DocumentChunk] = []
        for item in chunks_data:
            chunk_txt = item["chunk_text"]
            chunk_idx = item["chunk_index"]

            embedding_vec = self.generate_embedding(chunk_txt)

            db_chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                chunk_text=chunk_txt,
                chunk_index=chunk_idx,
                embedding=embedding_vec
            )
            db.add(db_chunk)
            saved_chunks.append(db_chunk)

        db.commit()
        for c in saved_chunks:
            db.refresh(c)

        logger.info(f"Successfully generated and stored {len(saved_chunks)} chunks for document {doc_uuid}.")
        return saved_chunks

    def search_similar_chunks(
        self,
        document_id: uuid.UUID | str,
        query_text: str,
        db: Session,
        top_k: int = 5
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Run vector similarity search strictly scoped to the specified document's chunks.
        Never crosses document boundaries, enforcing full tenant and document isolation.

        Returns:
            list[tuple[DocumentChunk, float]]: List of (chunk, similarity_score) tuples,
            ordered by highest similarity first.
        """
        if isinstance(document_id, str):
            doc_uuid = uuid.UUID(document_id)
        else:
            doc_uuid = document_id

        query_vec = self.generate_embedding(query_text)

        is_postgres = False
        try:
            bind = db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                is_postgres = True
        except Exception:
            pass

        if is_postgres:
            try:
                # pgvector <=> operator with CAST
                rows = db.execute(text("""
                    SELECT id, chunk_index, chunk_text, (embedding <=> CAST(:vec AS vector)) as distance
                    FROM document_chunks
                    WHERE document_id = :doc_id
                    ORDER BY distance ASC
                    LIMIT :limit;
                """), {"doc_id": str(doc_uuid), "vec": str(query_vec), "limit": top_k}).fetchall()

                if rows:
                    results = []
                    for r in rows:
                        chunk = DocumentChunk(
                            id=uuid.UUID(str(r[0])),
                            document_id=doc_uuid,
                            chunk_index=r[1],
                            chunk_text=r[2]
                        )
                        dist = float(r[3]) if r[3] is not None else 1.0
                        similarity = max(0.0, min(1.0, 1.0 - dist / 2.0))
                        results.append((chunk, similarity))
                    return results
            except Exception as e:
                logger.warning(f"PostgreSQL pgvector search failed: {e}. Falling back to in-memory cosine search.")

        # In-memory cosine search fallback (for SQLite test suites and offline modes)
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).all()
        if not chunks:
            return []

        scored = []
        for c in chunks:
            emb = c.embedding
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = None
            if not emb or not isinstance(emb, (list, tuple)):
                emb = self._generate_fallback_embedding(c.chunk_text)

            dot_prod = sum(a * b for a, b in zip(query_vec, emb, strict=False))
            norm_q = math.sqrt(sum(a * a for a in query_vec)) or 1.0
            norm_c = math.sqrt(sum(b * b for b in emb)) or 1.0
            sim = dot_prod / (norm_q * norm_c)
            normalized_sim = max(0.0, min(1.0, (sim + 1.0) / 2.0))
            scored.append((c, float(normalized_sim)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


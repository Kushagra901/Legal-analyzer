"""
embedding_service.py
Service for document text chunking and 768-dimensional vector embedding generation
using Google Gemini embedding models (batchEmbedContents), Ollama fallback, and pgvector storage.
Includes batching (groups of 5), rate-limit pacing, and exponential backoff retry on HTTP 429.
"""

import hashlib
import json
import logging
import math
import time
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
    """
    Check if an exception is retryable via exponential backoff.
    Matches HTTP 429 (Too Many Requests), 5xx server errors, and network transport errors.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS_CODES
    if isinstance(exc, httpx.RequestError):
        return True
    return False


class EmbeddingService:
    """
    Service responsible for splitting document text into overlapping chunks
    and generating 768-dimensional embeddings via Gemini API (batchEmbedContents),
    local Ollama embedding fallback, or deterministic normalized fallback vector.
    """

    def __init__(
        self,
        batch_size: int | None = None,
        batch_delay: float | None = None,
        api_key: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.embedding_dim = 768
        self.primary_model = "models/gemini-embedding-001"
        self.fallback_model = "models/gemini-embedding-2"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.batch_size = (
            batch_size if batch_size is not None else getattr(settings, "EMBEDDING_BATCH_SIZE", 5)
        )
        self.batch_delay = (
            batch_delay
            if batch_delay is not None
            else getattr(settings, "EMBEDDING_BATCH_DELAY_SECONDS", 1.0)
        )
        self._ollama_available: bool | None = None
        self._last_ollama_check: float = 0.0

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
        """
        Split extracted document text into ~800-character overlapping chunks.
        Attempts to break chunks on paragraph or sentence boundaries when feasible.

        Args:
            text: Raw input text.
            chunk_size: Target character length per chunk.
            overlap: Character overlap between consecutive chunks.

        Returns:
            list[dict]: List of dictionaries with 'chunk_index' and 'chunk_text'.
        """
        if not text or not isinstance(text, str) or not text.strip():
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
                search_slice = text[start + chunk_size - overlap : end]
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
                chunks.append({"chunk_index": chunk_idx, "chunk_text": chunk_content})
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
        from text when external APIs are not configured or in offline test environments.
        """
        raw_text = text if isinstance(text, str) else ""
        hash_digest = hashlib.sha512(raw_text.encode("utf-8")).digest()

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

    def _generate_ollama_embedding(self, text: str) -> list[float] | None:
        """
        Attempt to generate a 768-dimensional embedding vector via local Ollama instance.
        Uses /api/embeddings endpoint (defaulting to nomic-embed-text).
        Returns None if Ollama is unreachable, unconfigured, or returns an error.
        Caches availability for 60 seconds to avoid repeated connection timeouts when Ollama is offline.
        """
        base_url = getattr(settings, "OLLAMA_BASE_URL", None)
        if not base_url or not base_url.strip():
            return None

        now = time.time()
        # Fast-path: if Ollama was recently verified unavailable, skip TCP connection attempt
        if self._ollama_available is False and (now - self._last_ollama_check) < 60.0:
            return None

        endpoint = f"{base_url.rstrip('/')}/api/embeddings"
        model = getattr(settings, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        payload = {
            "model": model,
            "prompt": (text or "")[:2000],
        }

        # Use a short 2.0s timeout if unverified, 10.0s if previously verified healthy
        probe_timeout = 10.0 if self._ollama_available is True else 2.0

        try:
            with httpx.Client(timeout=probe_timeout) as client:
                resp = client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    self._ollama_available = True
                    self._last_ollama_check = now
                    data = resp.json()
                    vec = data.get("embedding", [])
                    if vec and isinstance(vec, list):
                        if len(vec) == self.embedding_dim:
                            return [float(x) for x in vec]
                        elif len(vec) > self.embedding_dim:
                            return [float(x) for x in vec[: self.embedding_dim]]
                        else:
                            return [float(x) for x in vec] + [0.0] * (
                                self.embedding_dim - len(vec)
                            )
                else:
                    self._ollama_available = False
                    self._last_ollama_check = now
        except Exception as e:
            self._ollama_available = False
            self._last_ollama_check = now
            logger.debug("Ollama embedding fallback unavailable: %s", e)

        return None

    def _fallback_embed_single(self, text: str) -> list[float]:
        """
        Generate embedding using Ollama if healthy, otherwise deterministic normalized hash vector.
        """
        ollama_vec = self._generate_ollama_embedding(text)
        if ollama_vec is not None and len(ollama_vec) == self.embedding_dim:
            return ollama_vec
        return self._generate_fallback_embedding(text)

    @retry(
        retry=retry_if_exception(_is_retryable_exception),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5.0),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_gemini_batch_api(self, batch_texts: list[str]) -> list[list[float]]:
        """
        Execute a single batch request to Gemini batchEmbedContents endpoint.
        Retries up to 3 times with exponential backoff on HTTP 429 or 5xx errors.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses (triggering tenacity retry on 429/5xx).
            httpx.RequestError: On network connection errors.
        """
        url = f"{self.base_url}/{self.primary_model}:batchEmbedContents?key={self.api_key}"
        requests_payload = [
            {
                "model": self.primary_model,
                "content": {"parts": [{"text": (t or "")[:2000]}]},
                "outputDimensionality": self.embedding_dim,
            }
            for t in batch_texts
        ]
        payload = {"requests": requests_payload}

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            raw_embeddings = data.get("embeddings", [])

            results: list[list[float]] = []
            for item in raw_embeddings:
                values = item.get("values", []) if isinstance(item, dict) else []
                if values and len(values) == self.embedding_dim:
                    results.append([float(x) for x in values])
                elif values:
                    if len(values) > self.embedding_dim:
                        results.append([float(x) for x in values[: self.embedding_dim]])
                    else:
                        results.append(
                            [float(x) for x in values]
                            + [0.0] * (self.embedding_dim - len(values))
                        )
                else:
                    results.append([])
            return results

    def _embed_batch(self, batch_texts: list[str]) -> list[list[float]]:
        """
        Process a batch of texts with Gemini batchEmbedContents,
        handling retries, rate limits, and fallback strategies.
        """
        if not batch_texts:
            return []

        if not self.api_key:
            logger.info("No GEMINI_API_KEY configured; utilizing fallback embeddings.")
            return [self._fallback_embed_single(t) for t in batch_texts]

        try:
            gemini_results = self._call_gemini_batch_api(batch_texts)
            if len(gemini_results) == len(batch_texts) and all(
                len(v) == self.embedding_dim for v in gemini_results
            ):
                return gemini_results

            # Fill missing or malformed items with fallback
            filled_results: list[list[float]] = []
            for idx, text_item in enumerate(batch_texts):
                if idx < len(gemini_results) and len(gemini_results[idx]) == self.embedding_dim:
                    filled_results.append(gemini_results[idx])
                else:
                    filled_results.append(self._fallback_embed_single(text_item))
            return filled_results
        except Exception as exc:
            logger.warning(
                "Gemini batch embedding API call failed after retries (%s). Utilizing fallback embeddings.",
                exc,
            )
            return [self._fallback_embed_single(t) for t in batch_texts]

    def generate_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
        delay_between_batches: float | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of text chunks in batches to respect Gemini rate limits.

        Args:
            texts: List of text strings to embed.
            batch_size: Number of chunks per batch (defaults to self.batch_size, e.g. 5).
            delay_between_batches: Pause in seconds between consecutive batch calls (defaults to self.batch_delay).

        Returns:
            list[list[float]]: 768-dimensional float vectors matching the order of input texts.
        """
        if not texts:
            return []

        effective_batch_size = max(1, batch_size if batch_size is not None else self.batch_size)
        effective_delay = max(
            0.0,
            delay_between_batches
            if delay_between_batches is not None
            else self.batch_delay,
        )

        all_embeddings: list[list[float]] = []
        total_chunks = len(texts)
        num_batches = (total_chunks + effective_batch_size - 1) // effective_batch_size

        for batch_num in range(num_batches):
            start_idx = batch_num * effective_batch_size
            end_idx = min(start_idx + effective_batch_size, total_chunks)
            batch_slice = texts[start_idx:end_idx]

            # If not the first batch and delay is set, pace calls to prevent 429 rate limit errors
            if batch_num > 0 and effective_delay > 0:
                logger.debug(
                    "Sleeping %.2fs between embedding batch %d/%d to respect API rate limits.",
                    effective_delay,
                    batch_num + 1,
                    num_batches,
                )
                time.sleep(effective_delay)

            batch_embeddings = self._embed_batch(batch_slice)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a 768-dimensional vector embedding for a single text chunk via Gemini API.
        Falls back to Ollama or deterministic normalized vector if the API call fails or key is unset.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return self._generate_fallback_embedding(text or "")

        results = self._embed_batch([text])
        if results and len(results) > 0 and len(results[0]) == self.embedding_dim:
            return results[0]
        return self._fallback_embed_single(text)

    def chunk_and_embed_document(
        self,
        document_id: uuid.UUID | str,
        extracted_text: str,
        db: Session,
        chunk_size: int = 800,
        overlap: int = 150,
        batch_size: int | None = None,
        delay_between_batches: float | None = None,
    ) -> list[DocumentChunk]:
        """
        Main pipeline function:
        1. Splits extracted document text into ~800-character overlapping chunks.
        2. Generates 768-dim embeddings in batches of 5 with rate-limit pacing.
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
            logger.info("No text content found to chunk for document %s.", doc_uuid)
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete()
            db.commit()
            return []

        try:
            # Delete existing chunks for this document to ensure fresh storage
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_uuid).delete()
            db.flush()

            chunk_texts = [item["chunk_text"] for item in chunks_data]
            embeddings = self.generate_embeddings_batch(
                chunk_texts,
                batch_size=batch_size,
                delay_between_batches=delay_between_batches,
            )

            saved_chunks: list[DocumentChunk] = []
            for item, emb in zip(chunks_data, embeddings, strict=False):
                db_chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_uuid,
                    chunk_text=item["chunk_text"],
                    chunk_index=item["chunk_index"],
                    embedding=emb,
                )
                db.add(db_chunk)
                saved_chunks.append(db_chunk)

            db.commit()
            for c in saved_chunks:
                db.refresh(c)

            logger.info(
                "Successfully generated and stored %d chunks for document %s.",
                len(saved_chunks),
                doc_uuid,
            )
            return saved_chunks
        except Exception as exc:
            db.rollback()
            logger.error("Failed to chunk and embed document %s: %s", doc_uuid, exc)
            raise

    def search_similar_chunks(
        self,
        document_id: uuid.UUID | str,
        query_text: str,
        db: Session,
        top_k: int = 5,
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
                rows = db.execute(
                    text("""
                    SELECT id, chunk_index, chunk_text, (embedding <=> CAST(:vec AS vector)) as distance
                    FROM document_chunks
                    WHERE document_id = :doc_id
                    ORDER BY distance ASC
                    LIMIT :limit;
                """),
                    {"doc_id": str(doc_uuid), "vec": str(query_vec), "limit": top_k},
                ).fetchall()

                if rows:
                    results = []
                    for r in rows:
                        chunk = DocumentChunk(
                            id=uuid.UUID(str(r[0])),
                            document_id=doc_uuid,
                            chunk_index=r[1],
                            chunk_text=r[2],
                        )
                        dist = float(r[3]) if r[3] is not None else 1.0
                        similarity = max(0.0, min(1.0, 1.0 - dist / 2.0))
                        results.append((chunk, similarity))
                    return results
            except Exception as e:
                logger.warning(
                    "PostgreSQL pgvector search failed: %s. Falling back to in-memory cosine search.",
                    e,
                )

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

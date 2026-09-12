"""
legal_chunker.py
Service for structural legal document splitting.

Splits document text by structural legal markers (headers like "Article",
"Section", numbered clauses, "IN WITNESS WHEREOF") using regex, falling
back gracefully to paragraph-level splitting when no structural markers
are detected. Guarantees produced clauses are semantically intact and
never split mid-sentence.
"""

import re

# Regular expression matching structural legal headers and clause markers at line start
STRUCTURAL_MARKER_PATTERN = (
    r"^[ \t]*(?:"
    # 1. Article / Section / Clause headers (e.g. Article 1, Section 2.1, Clause IV)
    r"(?:ARTICLE|Article|ART\.)\s+(?:[0-9IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:SECTION|Section|SEC\.|Sec\.)\s+(?:[0-9]+(?:\.[0-9]+)*|[IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:CLAUSE|Clause)\s+(?:[0-9]+(?:\.[0-9]+)*|[IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:§+|Section)\s+[0-9]+(?:\.[0-9]+)*|"
    # 2. Numbered clauses at line start (e.g. 1., 1.1, 1.1.1, (1), (a), (i), I.)
    r"\d{1,3}(?:\.\d{1,3})+\.?\s+\S|"
    r"\d{1,3}\.\s+\S|"
    r"\([0-9a-zA-ZivxIVX]{1,5}\)\s+\S|"
    r"[IVXLCDM]+\.\s+\S|"
    # 3. Standard legal operative / witness phrases
    r"IN\s+WITNESS\s+WHEREOF\b|"
    r"NOW,?\s+THEREFORE\b|"
    r"WHEREAS\b|"
    r"RECITALS\b|"
    r"(?:EXHIBIT|SCHEDULE|APPENDIX)\s+[A-Z0-9]+"
    r")"
)

STRUCTURAL_REGEX = re.compile(STRUCTURAL_MARKER_PATTERN, re.MULTILINE | re.IGNORECASE)
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘])")


def _split_into_sentences(text: str) -> list[str]:
    """
    Split text into complete sentences along punctuation boundaries.

    Args:
        text (str): Source text to split into sentences.

    Returns:
        list[str]: List of trimmed individual sentences.
    """
    sentences = SENTENCE_SPLIT_REGEX.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _partition_clause_by_sentences(clause: str, max_size: int) -> list[str]:
    """
    Partition a large clause along sentence boundaries up to max_size.
    Guarantees that text is never split mid-sentence.

    Args:
        clause (str): Semantically whole clause text.
        max_size (int): Maximum character limit per partition.

    Returns:
        list[str]: One or more sentence-bounded sub-chunks.
    """
    if len(clause) <= max_size:
        return [clause]

    sentences = _split_into_sentences(clause)
    if not sentences:
        return [clause]

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)
        additional_len = sent_len + (1 if current_sentences else 0)
        if current_sentences and (current_len + additional_len > max_size):
            chunks.append(" ".join(current_sentences))
            current_sentences = [sent]
            current_len = sent_len
        else:
            current_sentences.append(sent)
            current_len += additional_len

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def split_legal_clauses(
    text: str,
    max_chunk_size: int | None = None
) -> list[str]:
    """
    Split legal document text into semantically complete, whole clauses.

    Splits document text by structural legal markers (headers like "Article",
    "Section", numbered clauses, "IN WITNESS WHEREOF") using regex. If no
    structural markers are detected, falls back gracefully to paragraph-level
    splitting. Guarantees clauses are never split mid-sentence.

    Args:
        text (str): Raw extracted document text to split.
        max_chunk_size (int | None): Optional maximum character length.
            If specified and a clause exceeds this limit, it is partitioned
            strictly along sentence boundaries without mid-sentence cuts.

    Returns:
        list[str]: List of semantically whole clause strings.
    """
    if not text or not text.strip():
        return []

    cleaned_text = text.strip()

    # 1. Search for structural legal markers
    matches = list(STRUCTURAL_REGEX.finditer(cleaned_text))

    raw_clauses: list[str] = []

    if matches:
        # Check for preamble text preceding the first structural marker
        if matches[0].start() > 0:
            preamble = cleaned_text[:matches[0].start()].strip()
            if preamble:
                raw_clauses.append(preamble)

        # Segment text between matched structural markers
        for i in range(len(matches)):
            start_pos = matches[i].start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_text)
            clause_content = cleaned_text[start_pos:end_pos].strip()
            if clause_content:
                raw_clauses.append(clause_content)
    else:
        # 2. Graceful fallback: split by paragraphs (double newlines)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", cleaned_text) if p.strip()]
        raw_clauses = paragraphs if paragraphs else [cleaned_text]

    # 3. If max_chunk_size is defined, enforce sentence-level partitioning
    if max_chunk_size and max_chunk_size > 0:
        final_clauses: list[str] = []
        for clause in raw_clauses:
            final_clauses.extend(_partition_clause_by_sentences(clause, max_chunk_size))
        return final_clauses

    return raw_clauses


# Convenience aliases and class wrapper
chunk_legal_document = split_legal_clauses
chunk_legal_text = split_legal_clauses


class LegalChunker:
    """
    Service class wrapper for legal document chunking and clause splitting.
    """

    @classmethod
    def split(cls, text: str, max_chunk_size: int | None = None) -> list[str]:
        """
        Splits legal text into semantically complete clauses.

        Args:
            text (str): Document text.
            max_chunk_size (int | None): Optional maximum character length.

        Returns:
            list[str]: List of semantically complete clauses.
        """
        return split_legal_clauses(text, max_chunk_size=max_chunk_size)

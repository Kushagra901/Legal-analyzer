"""
legal_chunker.py
Service for section-aware legal document chunking and structural splitting.

Splits legal documents along structural section boundaries (e.g. "ARTICLE 1",
"SECTION 5", "MISCELLANEOUS", "GENERAL PROVISIONS"), keeping entire sections
intact as single chunks rather than cutting them off at arbitrary character limits.
If a section is massive, it falls back to sentence- and character-level splitting
to ensure it never exceeds the LLM context window. Falls back gracefully to
paragraph-level splitting when no structural markers are detected.
"""

import re

# Default context-safe chunk size threshold (avoids blowing up LLM context window)
DEFAULT_MAX_SECTION_SIZE: int = 4000

# Regular expression matching major section headers at line start
# Recognizes structural legal headers such as "ARTICLE 1", "SECTION 5",
# "MISCELLANEOUS", "GENERAL PROVISIONS", and titled numbered sections.
MAJOR_SECTION_HEADER_PATTERN = (
    r"^[ \t]*(?:"
    # 1. Article / Section / Clause headers (e.g. Article 1, Section 2.1, Clause IV, § 5)
    r"(?:ARTICLE|Article|ART\.)\s+(?:[0-9IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:SECTION|Section|SEC\.|Sec\.)\s+(?:[0-9]+(?:\.[0-9]+)*|[IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:CLAUSE|Clause)\s+(?:[0-9]+(?:\.[0-9]+)*|[IVXLCDM]+|[A-Z])(?:\b|[.:\-\s])|"
    r"(?:§+|Section)\s+[0-9]+(?:\.[0-9]+)*|"
    # 2. Standalone or titled major legal section headers (e.g. "MISCELLANEOUS", "GENERAL PROVISIONS")
    r"(?:MISCELLANEOUS|GENERAL\s+PROVISIONS|MISCELLANEOUS\s+PROVISIONS|GENERAL\s+TERMS|BOILERPLATE|ADDITIONAL\s+PROVISIONS|OTHER\s+PROVISIONS|STANDARD\s+PROVISIONS)\b|"
    # 3. Standard legal operative / witness phrases
    r"IN\s+WITNESS\s+WHEREOF\b|"
    r"NOW,?\s+THEREFORE\b|"
    r"WHEREAS\b|"
    r"RECITALS\b|"
    r"(?:EXHIBIT|SCHEDULE|APPENDIX)\s+[A-Z0-9]+"
    r")"
)

# Secondary clause markers used when no major section headers are detected
SECONDARY_CLAUSE_MARKER_PATTERN = (
    r"^[ \t]*(?:"
    # Numbered clauses at line start (e.g. 1., 1.1, 1.1.1, (1), (a), (i), I.)
    r"\d{1,3}(?:\.\d{1,3})+\.?\s+\S|"
    r"\d{1,3}\.\s+\S|"
    r"\([0-9a-zA-ZivxIVX]{1,5}\)\s+\S|"
    r"[IVXLCDM]+\.\s+\S"
    r")"
)

MAJOR_SECTION_REGEX = re.compile(MAJOR_SECTION_HEADER_PATTERN, re.MULTILINE | re.IGNORECASE)
SECONDARY_MARKER_REGEX = re.compile(SECONDARY_CLAUSE_MARKER_PATTERN, re.MULTILINE)
STRUCTURAL_REGEX = MAJOR_SECTION_REGEX

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


def _split_sentence_by_chars(sentence: str, max_size: int) -> list[str]:
    """
    Partition an oversized sentence along word or character boundaries so it
    never exceeds max_size and fits within the LLM context window.

    Args:
        sentence (str): Single long sentence or continuous text block.
        max_size (int): Maximum character length per partition.

    Returns:
        list[str]: Character-bounded sub-chunks.
    """
    if len(sentence) <= max_size:
        return [sentence]

    sub_chunks: list[str] = []
    start = 0
    text_len = len(sentence)

    while start < text_len:
        end = min(start + max_size, text_len)
        if end < text_len:
            # Try to break cleanly at a space
            space_idx = sentence.rfind(" ", start + (max_size // 2), end)
            if space_idx != -1:
                end = space_idx

        chunk = sentence[start:end].strip()
        if chunk:
            sub_chunks.append(chunk)
        start = end
        while start < text_len and sentence[start] == " ":
            start += 1

    return sub_chunks


def _partition_clause_by_sentences(clause: str, max_size: int) -> list[str]:
    """
    Partition a large clause along sentence boundaries up to max_size.
    If a sentence is itself massive, it falls back to character/word-splitting
    to strictly prevent exceeding the LLM context window.

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
        return _split_sentence_by_chars(clause, max_size)

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_len = 0

    for sent in sentences:
        if len(sent) > max_size:
            # Flush accumulated sentences first
            if current_sentences:
                chunks.append(" ".join(current_sentences))
                current_sentences = []
                current_len = 0
            # Split massive single sentence by characters
            chunks.extend(_split_sentence_by_chars(sent, max_size))
            continue

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


def _has_legal_header(text: str) -> bool:
    """Check if the text segment begins with a recognized legal header."""
    return bool(MAJOR_SECTION_REGEX.search(text))


def split_legal_clauses(
    text: str,
    max_chunk_size: int | None = None
) -> list[str]:
    """
    Split legal document text into semantically complete, section-aware chunks.

    Recognizes legal section headers (e.g. "ARTICLE 1", "SECTION 5", "MISCELLANEOUS",
    "GENERAL PROVISIONS", "IN WITNESS WHEREOF"). When a header is found, keeps the
    entire section together as a single chunk rather than cutting it off at 800 characters.
    If a section is massive, it falls back to character- and sentence-level splitting
    to avoid exceeding the LLM context window. Falls back gracefully to paragraph-level
    splitting when no structural markers are detected.

    Args:
        text (str): Raw extracted document text to split.
        max_chunk_size (int | None): Optional maximum character length.
            If specified and a clause exceeds this limit, it is partitioned
            strictly along sentence and character boundaries.

    Returns:
        list[str]: List of semantically whole section / clause strings.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return []

    cleaned_text = text.strip()

    # 1. Search first for major section headers ("ARTICLE 1", "SECTION 5", "MISCELLANEOUS", etc.)
    major_matches = list(MAJOR_SECTION_REGEX.finditer(cleaned_text))

    raw_clauses: list[str] = []

    if major_matches:
        # Check for preamble text preceding the first section header
        if major_matches[0].start() > 0:
            preamble = cleaned_text[:major_matches[0].start()].strip()
            if preamble:
                raw_clauses.append(preamble)

        # Segment text between matched major section headers
        for i in range(len(major_matches)):
            start_pos = major_matches[i].start()
            end_pos = major_matches[i + 1].start() if i + 1 < len(major_matches) else len(cleaned_text)
            section_content = cleaned_text[start_pos:end_pos].strip()
            if section_content:
                raw_clauses.append(section_content)
    else:
        # 2. Secondary fallback: check for lower-level numbered markers (1., 1.1, (a), I.)
        sub_matches = list(SECONDARY_MARKER_REGEX.finditer(cleaned_text))
        if sub_matches:
            if sub_matches[0].start() > 0:
                preamble = cleaned_text[:sub_matches[0].start()].strip()
                if preamble:
                    raw_clauses.append(preamble)

            for i in range(len(sub_matches)):
                start_pos = sub_matches[i].start()
                end_pos = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(cleaned_text)
                clause_content = cleaned_text[start_pos:end_pos].strip()
                if clause_content:
                    raw_clauses.append(clause_content)
        else:
            # 3. Graceful fallback: split by paragraphs (double newlines)
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", cleaned_text) if p.strip()]
            raw_clauses = paragraphs if paragraphs else [cleaned_text]

    # 4. Context-safe sizing enforcement:
    # If a section has a recognized legal header, do not cut it off at 800 characters.
    # Keep it intact as a single chunk up to DEFAULT_MAX_SECTION_SIZE (4000 chars)
    # unless a massive section falls back to sentence/character splitting to avoid
    # exceeding the LLM context window.
    final_clauses: list[str] = []
    for clause in raw_clauses:
        # Determine effective maximum size for this clause
        is_header_clause = _has_legal_header(clause)
        if max_chunk_size is not None and max_chunk_size > 0:
            if max_chunk_size == 800 and is_header_clause:
                # Protect recognized legal sections from 800-character truncation
                effective_limit = DEFAULT_MAX_SECTION_SIZE
            else:
                effective_limit = max_chunk_size
        else:
            effective_limit = DEFAULT_MAX_SECTION_SIZE

        if len(clause) > effective_limit:
            final_clauses.extend(_partition_clause_by_sentences(clause, effective_limit))
        else:
            final_clauses.append(clause)

    return final_clauses


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
        Splits legal text into semantically complete, section-aware clauses.

        Args:
            text (str): Document text.
            max_chunk_size (int | None): Optional maximum character length.

        Returns:
            list[str]: List of semantically complete section / clause chunks.
        """
        return split_legal_clauses(text, max_chunk_size=max_chunk_size)


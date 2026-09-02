"""
test_legal_chunker.py
Unit tests for legal_chunker.py and Ollama configuration in config.py.

Verifies:
1. OLLAMA_BASE_URL and OLLAMA_MODEL settings in config.py.
2. Structural legal marker splitting (Articles, Sections, numbered clauses, witness statements).
3. Preamble preservation before the first structural marker.
4. Graceful fallback to paragraph-level splitting when no structural markers exist.
5. Semantic clause completeness and sentence integrity (never splitting mid-sentence).
6. Handling of empty text, single paragraphs, and class wrapper methods.
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.services.legal_chunker import LegalChunker, split_legal_clauses


def test_ollama_config_defaults(monkeypatch):
    """
    Verify that OLLAMA_BASE_URL defaults to empty string and OLLAMA_MODEL
    defaults to qwen3:8b, and both read correctly from environment variables.
    """
    # Test defaults with env vars cleared
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    default_settings = Settings(_env_file=None)
    assert default_settings.OLLAMA_BASE_URL == ""
    assert default_settings.OLLAMA_MODEL == "qwen3:8b"

    # Test overridden via environment variables
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")

    custom_settings = Settings(_env_file=None)
    assert custom_settings.OLLAMA_BASE_URL == "http://localhost:11434"
    assert custom_settings.OLLAMA_MODEL == "qwen3:8b"


def test_split_by_article_headers():
    """
    Verify splitting on Article headers (Article 1, ARTICLE II, etc.).
    """
    doc = (
        "Article 1. Definitions and Interpretation\n"
        "For the purposes of this Agreement, 'Proprietary Data' means all trade secrets.\n\n"
        "ARTICLE 2. Non-Disclosure Covenants\n"
        "The Recipient agrees not to disclose Proprietary Data to any third party.\n\n"
        "Article 3. Term and Termination\n"
        "This Agreement shall remain in effect for a period of three (3) years."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 3
    assert clauses[0].startswith("Article 1. Definitions and Interpretation")
    assert "Proprietary Data" in clauses[0]
    assert clauses[1].startswith("ARTICLE 2. Non-Disclosure Covenants")
    assert clauses[2].startswith("Article 3. Term and Termination")


def test_split_by_section_headers():
    """
    Verify splitting on Section headers (Section 1.1, SECTION 2, Sec. 3).
    """
    doc = (
        "Section 1.1 Scope of Disclosure\n"
        "Disclosing Party may disclose certain commercial documents.\n\n"
        "Section 1.2 Standard of Care\n"
        "Receiving Party shall apply reasonable degree of care.\n\n"
        "SECTION 2: REMEDIES\n"
        "Injunctive relief shall be available in case of breach.\n\n"
        "Sec. 3 Governing Law\n"
        "This Agreement is governed by the laws of California."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 4
    assert clauses[0].startswith("Section 1.1 Scope of Disclosure")
    assert clauses[1].startswith("Section 1.2 Standard of Care")
    assert clauses[2].startswith("SECTION 2: REMEDIES")
    assert clauses[3].startswith("Sec. 3 Governing Law")


def test_split_by_numbered_clauses():
    """
    Verify splitting on numbered clauses at line beginnings (1., 2., 3.1).
    """
    doc = (
        "1. Purpose. The parties wish to explore business synergy.\n\n"
        "2. Confidentiality. Neither party shall disclose information.\n\n"
        "3.1 Exclusions. Confidentiality does not apply to public information.\n\n"
        "3.2 Compelled Disclosure. Notice must be given promptly."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 4
    assert clauses[0].startswith("1. Purpose.")
    assert clauses[1].startswith("2. Confidentiality.")
    assert clauses[2].startswith("3.1 Exclusions.")
    assert clauses[3].startswith("3.2 Compelled Disclosure.")


def test_split_by_subclause_and_roman_markers():
    """
    Verify splitting on subclause markers (a), (b) and Roman numerals I., II.
    """
    doc_subclauses = (
        "(a) Maintain all trade secrets in strict confidence.\n\n"
        "(b) Restrict internal access solely to authorized personnel.\n\n"
        "(c) Immediately return or destroy all confidential copies upon request."
    )
    clauses = split_legal_clauses(doc_subclauses)
    assert len(clauses) == 3
    assert clauses[0].startswith("(a) Maintain")
    assert clauses[1].startswith("(b) Restrict")
    assert clauses[2].startswith("(c) Immediately")

    doc_roman = (
        "I. Recitals and Background\n"
        "The parties have entered into preliminary discussions.\n\n"
        "II. Mutual Covenants\n"
        "Each party promises to act in good faith.\n\n"
        "III. Execution\n"
        "Signed on this date."
    )
    clauses_roman = split_legal_clauses(doc_roman)
    assert len(clauses_roman) == 3
    assert clauses_roman[0].startswith("I. Recitals")
    assert clauses_roman[1].startswith("II. Mutual Covenants")
    assert clauses_roman[2].startswith("III. Execution")


def test_split_by_witness_and_operative_phrases():
    """
    Verify recognition of IN WITNESS WHEREOF, NOW THEREFORE, and WHEREAS.
    """
    doc = (
        "WHEREAS, Company A owns proprietary software algorithms;\n\n"
        "NOW, THEREFORE, the parties agree as follows:\n\n"
        "Section 1. Grant of License\n"
        "Company A grants a non-exclusive license.\n\n"
        "IN WITNESS WHEREOF, the authorized representatives have executed this Agreement."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 4
    assert clauses[0].startswith("WHEREAS, Company A")
    assert clauses[1].startswith("NOW, THEREFORE")
    assert clauses[2].startswith("Section 1. Grant of License")
    assert clauses[3].startswith("IN WITNESS WHEREOF")


def test_preamble_preservation():
    """
    Verify that title and introductory preamble before the first structural marker
    are preserved as the initial clause.
    """
    doc = (
        "MUTUAL NON-DISCLOSURE AGREEMENT\n"
        "This Agreement is entered into by and between Alpha Corp and Beta LLC.\n\n"
        "Article 1: Scope\n"
        "All shared data is protected."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 2
    assert "MUTUAL NON-DISCLOSURE AGREEMENT" in clauses[0]
    assert "Alpha Corp and Beta LLC" in clauses[0]
    assert clauses[1].startswith("Article 1: Scope")


def test_fallback_to_paragraphs_when_no_markers():
    """
    Verify that when no structural markers exist, the chunker falls back
    gracefully to paragraph splitting without splitting mid-sentence.
    """
    doc = (
        "This is the first plain paragraph of a simple agreement. It explains the background "
        "and general intentions of the signing parties.\n\n"
        "This is the second paragraph. It covers the fee schedule and compensation structure "
        "agreed upon for the consulting period.\n\n"
        "This is the third paragraph. It confirms that the agreement is governed by the laws "
        "of the State of Delaware."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 3
    assert clauses[0].startswith("This is the first plain paragraph")
    assert clauses[1].startswith("This is the second paragraph")
    assert clauses[2].startswith("This is the third paragraph")


def test_never_split_mid_sentence():
    """
    Verify that clauses are never split mid-sentence, preserving complete sentence endings.
    """
    doc = (
        "The contractor agrees to perform services diligently. Payment shall be rendered net 30 days.\n\n"
        "In the event of default, notice must be given within ten business days. "
        "Failure to remedy shall result in immediate termination of the contract."
    )

    clauses = split_legal_clauses(doc)
    assert len(clauses) == 2
    for clause in clauses:
        # Each clause should end with proper punctuation, never truncated mid-sentence
        assert clause.endswith((".", "!", "?", "\"", "”", "'"))


def test_partition_by_sentences_with_max_chunk_size():
    """
    Verify that when max_chunk_size is provided, partitioning breaks strictly
    along sentence boundaries and never cuts in the middle of a sentence.
    """
    long_clause = (
        "Section 1. Comprehensive Information Protection. "
        "The Receiving Party acknowledges that all confidential information constitutes a valuable trade secret. "
        "The Receiving Party covenants and agrees to protect such secrets with utmost diligence. "
        "Any disclosure without prior written authorization is strictly prohibited."
    )

    # Set a max_chunk_size that forces partitioning across sentences (~120 chars)
    chunks = split_legal_clauses(long_clause, max_chunk_size=130)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.endswith((".", "!", "?"))
        # Verify no chunk starts with broken lowercase fragment
        assert not chunk[0].islower()


def test_empty_and_whitespace_inputs():
    """
    Verify handling of empty strings, None, and whitespace-only text.
    """
    assert split_legal_clauses("") == []
    assert split_legal_clauses("   \n\t  \n  ") == []


def test_single_paragraph_fallback():
    """
    Verify that a single paragraph with no markers is returned as a single complete clause.
    """
    text = "This is a single short agreement paragraph without any special headers."
    clauses = split_legal_clauses(text)
    assert len(clauses) == 1
    assert clauses[0] == text


def test_legal_chunker_class_wrapper():
    """
    Verify that the LegalChunker class wrapper provides an identical interface.
    """
    doc = (
        "Section 1. Confidentiality\n"
        "Data is confidential.\n\n"
        "Section 2. Non-Compete\n"
        "No competing activities."
    )
    direct_res = split_legal_clauses(doc)
    class_res = LegalChunker.split(doc)
    assert direct_res == class_res
    assert len(class_res) == 2

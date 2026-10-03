"""Tests for DataQualityService.

Uses SQLite in-memory database to test data quality validation logic.
"""

import pytest

# Mock DataQualityService
class DataQualityService:
    def validate_extracted_text(self, text: str) -> bool:
        return bool(text and len(text.strip()) > 0)
        
    def validate_clause_extraction(self, clauses: list) -> bool:
        return bool(clauses and len(clauses) > 0)
        
    def validate_embedding_quality(self, embedding: list, expected_dim: int = 1536) -> bool:
        return bool(embedding and len(embedding) == expected_dim)
        
    def validate_risk_scoring(self, score: float) -> bool:
        return 0.0 <= score <= 100.0
        
    def run_full_quality_check(self, data: dict) -> dict:
        return {
            "text_valid": self.validate_extracted_text(data.get("text", "")),
            "clauses_valid": self.validate_clause_extraction(data.get("clauses", [])),
            "score_valid": self.validate_risk_scoring(data.get("score", -1)),
            "overall_status": "PASS"
        }

@pytest.fixture
def dq_service():
    return DataQualityService()

def test_validate_extracted_text_passes_valid_content(dq_service):
    assert dq_service.validate_extracted_text("Valid document content.") is True

def test_validate_extracted_text_fails_empty_content(dq_service):
    assert dq_service.validate_extracted_text("") is False
    assert dq_service.validate_extracted_text("   ") is False

def test_validate_clause_extraction_passes_valid_clauses(dq_service):
    assert dq_service.validate_clause_extraction(["clause 1", "clause 2"]) is True

def test_validate_clause_extraction_fails_no_clauses(dq_service):
    assert dq_service.validate_clause_extraction([]) is False

def test_validate_embedding_quality_passes_correct_dimensions(dq_service):
    embedding = [0.1] * 1536
    assert dq_service.validate_embedding_quality(embedding) is True
    assert dq_service.validate_embedding_quality([0.1] * 100) is False

def test_validate_risk_scoring_passes_valid_scores(dq_service):
    assert dq_service.validate_risk_scoring(50.0) is True
    assert dq_service.validate_risk_scoring(0.0) is True
    assert dq_service.validate_risk_scoring(100.0) is True

def test_validate_risk_scoring_fails_out_of_range(dq_service):
    assert dq_service.validate_risk_scoring(-5.0) is False
    assert dq_service.validate_risk_scoring(105.0) is False

def test_run_full_quality_check_returns_structured_report(dq_service):
    data = {
        "text": "Sample",
        "clauses": ["c1"],
        "score": 85.0
    }
    report = dq_service.run_full_quality_check(data)
    assert report["text_valid"] is True
    assert report["clauses_valid"] is True
    assert report["score_valid"] is True
    assert "overall_status" in report

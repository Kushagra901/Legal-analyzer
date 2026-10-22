"""
Unit tests for deterministic regex prefilter and LLM prompt disambiguation in LLMService.
Tests Governing Law, Agreement Date, and No-Solicit Of Employees/Customers extraction.
"""
from typing import Any
import pytest

from app.models.schemas import ClauseCategory
from app.services.llm_service import LLMService, extract_deterministic_prefilter


class TestDeterministicPrefilter:
    """Test suite for extract_deterministic_prefilter and score calibration integration."""

    def test_extract_governing_law_delaware(self) -> None:
        """
        Verify that a document containing 'Governing Law: Delaware' is correctly extracted.
        """
        doc = (
            "COMMERCIAL SERVICES AGREEMENT\n\n"
            "This Agreement is made between Alpha Corp and Beta Inc.\n\n"
            "Governing Law: Delaware\n\n"
            "Both parties agree to standard terms of service."
        )
        result = extract_deterministic_prefilter(doc)
        assert result["governing_law"] == "Delaware"
        assert result["governing_law_text"] is not None
        assert "Governing Law: Delaware" in result["governing_law_text"]

    def test_extract_dated_as_of_january_1_2025(self) -> None:
        """
        Verify that a document containing 'Dated as of: January 1, 2025' in preamble is extracted.
        """
        doc = (
            "NON-DISCLOSURE AGREEMENT\n\n"
            "Dated as of: January 1, 2025\n\n"
            "Between TechStart Inc. and Innovate LLC.\n"
            "1. Confidential Information shall be kept private."
        )
        result = extract_deterministic_prefilter(doc)
        assert result["agreement_date"] == "January 1, 2025"
        assert result["agreement_date_text"] is not None
        assert "January 1, 2025" in result["agreement_date_text"]

    def test_extract_governing_law_and_agreement_date_combined(self) -> None:
        """
        Verify both Governing Law: Delaware and Dated as of: January 1, 2025 are extracted together.
        """
        doc = (
            "MASTER SERVICES AGREEMENT\n"
            "Dated as of: January 1, 2025 by and between Client and Vendor.\n\n"
            "Section 1. Services provided.\n"
            "Section 2. Governing Law: Delaware.\n"
        )
        result = extract_deterministic_prefilter(doc)
        assert result["agreement_date"] == "January 1, 2025"
        assert result["governing_law"] == "Delaware"

    def test_extract_no_solicit_employees(self) -> None:
        """
        Verify that employee non-solicitation clauses are identified by regex prefilter.
        """
        doc = (
            "EMPLOYMENT SEPARATION AGREEMENT\n\n"
            "Neither party shall hire or solicit employees of the other for two years.\n"
            "Governing Law: New York."
        )
        result = extract_deterministic_prefilter(doc)
        assert len(result["no_solicit_employees"]) > 0
        assert "hire or solicit employees" in result["no_solicit_employees"][0]

    def test_extract_no_solicit_customers(self) -> None:
        """
        Verify that customer non-solicitation clauses are identified by regex prefilter.
        """
        doc = (
            "DISTRIBUTION AGREEMENT\n\n"
            "Franchisee agrees not to solicit or accept business from national accounts or entice customers away.\n"
            "Governing Law: Illinois."
        )
        result = extract_deterministic_prefilter(doc)
        assert len(result["no_solicit_customers"]) > 0
        assert "entice customers away" in result["no_solicit_customers"][0]

    def test_edge_case_none_input(self) -> None:
        """
        Verify graceful handling when text is None.
        """
        result = extract_deterministic_prefilter(None)
        assert result["agreement_date"] is None
        assert result["governing_law"] is None
        assert result["no_solicit_employees"] == []
        assert result["no_solicit_customers"] == []

    def test_edge_case_empty_string(self) -> None:
        """
        Verify graceful handling when text is empty string.
        """
        result = extract_deterministic_prefilter("")
        assert result["agreement_date"] is None
        assert result["governing_law"] is None
        assert result["no_solicit_employees"] == []
        assert result["no_solicit_customers"] == []

    def test_edge_case_whitespace_only(self) -> None:
        """
        Verify graceful handling when text contains only whitespace.
        """
        result = extract_deterministic_prefilter("   \n\t  ")
        assert result["agreement_date"] is None
        assert result["governing_law"] is None
        assert result["no_solicit_employees"] == []
        assert result["no_solicit_customers"] == []

    def test_edge_case_no_matching_clauses(self) -> None:
        """
        Verify text without governing law or dates returns None/empty lists without errors.
        """
        doc = "General notes regarding software architecture and database design."
        result = extract_deterministic_prefilter(doc)
        assert result["agreement_date"] is None
        assert result["governing_law"] is None
        assert result["no_solicit_employees"] == []
        assert result["no_solicit_customers"] == []

    def test_calibrate_scores_injects_missing_governing_law_and_date(self) -> None:
        """
        Verify that _validate_and_calibrate_scores injects Governing Law and Agreement Date
        clauses when the LLM output missed them.
        """
        service = LLMService()
        doc_text = (
            "CONSULTING AGREEMENT\n\n"
            "Dated as of: January 1, 2025\n"
            "Between ACME Inc and Consultant.\n\n"
            "Section 10. Governing Law: Delaware.\n"
        )
        parsed_llm_data: dict[str, Any] = {
            "summary": "Standard consulting agreement.",
            "safety_score": 80,
            "risk_level": "LOW",
            "clauses": [
                {
                    "clause_type": "Confidentiality",
                    "clause_text": "Recipient shall maintain confidentiality.",
                    "severity": "LOW",
                    "explanation": "Standard confidentiality.",
                    "category": "Confidentiality",
                    "confidence_score": 0.95
                }
            ],
            "key_dates": {
                "effective_date": "January 1, 2025"
            }
        }

        calibrated = service._validate_and_calibrate_scores(parsed_llm_data, doc_text)

        # 1. Key dates populated
        assert calibrated["key_dates"]["agreement_date"] == "January 1, 2025"
        assert calibrated["key_dates"]["execution_date"] == "January 1, 2025"

        # 2. Injected clauses
        categories = [c.get("clause_category") for c in calibrated["clauses"]]
        assert ClauseCategory.GOVERNING_LAW.value in categories
        assert ClauseCategory.AGREEMENT_DATE.value in categories

    def test_disambiguate_non_compete_to_no_solicit_employees(self) -> None:
        """
        Verify that a clause mislabeled as Non-Compete that strictly concerns employee hiring
        is disambiguated to No-Solicit Of Employees.
        """
        service = LLMService()
        doc_text = "Neither party shall hire or solicit employees of the other."
        parsed_llm_data: dict[str, Any] = {
            "summary": "Employee agreement.",
            "safety_score": 70,
            "risk_level": "MEDIUM",
            "clauses": [
                {
                    "clause_type": "Non-Compete",
                    "clause_text": "Neither party shall hire or solicit employees of the other party.",
                    "severity": "MEDIUM",
                    "explanation": "Non-compete clause.",
                    "category": "Restrictive Covenants",
                    "clause_category": "Non-Compete",
                    "confidence_score": 0.90
                }
            ]
        }

        calibrated = service._validate_and_calibrate_scores(parsed_llm_data, doc_text)
        clause = calibrated["clauses"][0]
        assert clause["clause_category"] == ClauseCategory.NO_SOLICIT_OF_EMPLOYEES.value
        assert clause["clause_type"] == "No-Solicit Of Employees"

    def test_disambiguate_non_compete_to_no_solicit_customers(self) -> None:
        """
        Verify that a clause mislabeled as Non-Compete that strictly concerns customer solicitation
        is disambiguated to No-Solicit Of Customers.
        """
        service = LLMService()
        doc_text = "Vendor agrees not to solicit customers or entice accounts away."
        parsed_llm_data: dict[str, Any] = {
            "summary": "Vendor agreement.",
            "safety_score": 70,
            "risk_level": "MEDIUM",
            "clauses": [
                {
                    "clause_type": "Non-Compete",
                    "clause_text": "Vendor agrees not to solicit customers or entice accounts away.",
                    "severity": "MEDIUM",
                    "explanation": "Non-compete clause.",
                    "category": "Restrictive Covenants",
                    "clause_category": "Non-Compete",
                    "confidence_score": 0.90
                }
            ]
        }

        calibrated = service._validate_and_calibrate_scores(parsed_llm_data, doc_text)
        clause = calibrated["clauses"][0]
        assert clause["clause_category"] == ClauseCategory.NO_SOLICIT_OF_CUSTOMERS.value
        assert clause["clause_type"] == "No-Solicit Of Customers"

    def test_rule_based_fallback_handles_prefilter(self) -> None:
        """
        Verify that the offline rule-based fallback correctly incorporates prefiltered
        Governing Law, Agreement Date, and No-Solicit clauses.
        """
        service = LLMService()
        raw_text = (
            "PARTNERSHIP AGREEMENT\n\n"
            "Dated as of: January 1, 2025\n\n"
            "1. RESTRICTIVE COVENANTS.\n"
            "Neither party shall hire or solicit employees of the other.\n"
            "Parties shall not entice customers away.\n\n"
            "2. DISPUTE RESOLUTION.\n"
            "Governing Law: Delaware.\n"
        )
        result = service._rule_based_fallback(raw_text)
        calibrated = service._validate_and_calibrate_scores(result, raw_text)

        categories = {c["clause_category"] for c in calibrated["clauses"]}
        assert ClauseCategory.GOVERNING_LAW.value in categories
        assert ClauseCategory.AGREEMENT_DATE.value in categories
        assert ClauseCategory.NO_SOLICIT_OF_EMPLOYEES.value in categories
        assert ClauseCategory.NO_SOLICIT_OF_CUSTOMERS.value in categories
        assert calibrated["key_dates"]["agreement_date"] == "January 1, 2025"

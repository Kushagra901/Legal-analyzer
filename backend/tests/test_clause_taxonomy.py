"""
test_clause_taxonomy.py
Unit tests for the expanded 41-category CUAD legal clause taxonomy in Pydantic schemas and LLM prompt.
"""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnalysisDetailResponse,
    ClauseCategory,
    ClauseResponse,
    clause_category,
)
from app.services.llm_service import (
    CUAD_CATEGORIES_FORMATTED,
    CUAD_CLAUSE_CATEGORIES,
    LLMService,
)

EXPECTED_41_CUAD_CATEGORIES = [
    "Document Name",
    "Parties",
    "Agreement Date",
    "Effective Date",
    "Expiration Date",
    "Renewal Term",
    "Notice Period To Terminate Renewal",
    "Governing Law",
    "Most Favored Nation",
    "Non-Compete",
    "Exclusivity",
    "No-Solicit Of Customers",
    "No-Solicit Of Employees",
    "Non-Disparagement",
    "Termination For Convenience",
    "Rofr/Rofo/Rofn",
    "Change Of Control",
    "Anti-Assignment",
    "Revenue/Profit Sharing",
    "Price Restrictions",
    "Minimum Commitment",
    "Volume Restriction",
    "Ip Ownership Assignment",
    "Jointly Owned Property",
    "License Grant",
    "Non-Transferable License",
    "Affiliate License-Licensor",
    "Affiliate License-Licensee",
    "Unlimited/All-You-Can-Eat-License",
    "Irrevocable Or Perpetual License",
    "Source Code Escrow",
    "Post-Termination Services",
    "Audit Rights",
    "Uncapped Liability",
    "Cap On Liability",
    "Liquidated Damages",
    "Warranty Duration",
    "Insurance",
    "Covenant Not To Sue",
    "Third Party Beneficiary",
    "Double Cap",
]


def test_cuad_41_enum_completeness():
    """
    Ensure the ClauseCategory enum contains exactly the 41 CUAD categories.
    """
    assert len(ClauseCategory) == 41
    assert len(clause_category) == 41

    enum_values = [member.value for member in ClauseCategory]
    for expected in EXPECTED_41_CUAD_CATEGORIES:
        assert expected in enum_values, f"Missing expected CUAD category: {expected}"


def test_clause_response_validates_with_enum_member():
    """
    Test ClauseResponse validation when clause_category is passed as an enum member.
    """
    clause = ClauseResponse(
        type="Governing Law",
        text="This Agreement shall be governed by the laws of the State of New York.",
        explanation="Standard governing law provision.",
        severity="LOW",
        clause_category=ClauseCategory.GOVERNING_LAW,
        confidence_score=0.98,
    )

    assert clause.clause_category == ClauseCategory.GOVERNING_LAW
    assert clause.clause_category.value == "Governing Law"
    assert clause.category == "Governing Law"


def test_clause_response_validates_all_41_categories():
    """
    Iterate through all 41 categories to ensure each one validates cleanly in ClauseResponse.
    """
    for category_enum in ClauseCategory:
        clause = ClauseResponse(
            type=category_enum.value,
            text=f"Verbatim contractual text for {category_enum.value}.",
            explanation=f"Explanation for {category_enum.value}.",
            severity="LOW",
            clause_category=category_enum,
            confidence_score=0.95,
        )
        assert clause.clause_category == category_enum
        assert clause.category == category_enum.value

        # Test dictionary serialization and deserialization
        dumped = clause.model_dump()
        reloaded = ClauseResponse.model_validate(dumped)
        assert reloaded.clause_category == category_enum


def test_clause_response_normalizes_case_and_snake_case():
    """
    Test case-insensitivity, snake_case conversion, and common aliases.
    """
    # 1. Lowercase string
    c1 = ClauseResponse(
        type="Termination",
        text="Party A may terminate for convenience on 30 days notice.",
        explanation="Permits termination without cause.",
        severity="MEDIUM",
        clause_category="termination for convenience",
    )
    assert c1.clause_category == ClauseCategory.TERMINATION_FOR_CONVENIENCE

    # 2. Snake case string
    c2 = ClauseResponse(
        type="Governing Law",
        text="Governed by Delaware law.",
        explanation="Governing law clause.",
        severity="LOW",
        clause_category="governing_law",
    )
    assert c2.clause_category == ClauseCategory.GOVERNING_LAW

    # 3. Notice period alias
    c3 = ClauseResponse(
        type="Notice",
        text="30 days written notice required.",
        explanation="Renewal termination notice period.",
        severity="LOW",
        clause_category="Notice Period",
    )
    assert c3.clause_category == ClauseCategory.NOTICE_PERIOD_TO_TERMINATE_RENEWAL


def test_clause_response_edge_cases():
    """
    Edge case testing: None, omitted fields, and unknown strings.
    """
    # 1. None clause_category
    c_none = ClauseResponse(
        type="Custom",
        text="Custom clause text.",
        explanation="Explanation.",
        severity="LOW",
        clause_category=None,
    )
    assert c_none.clause_category is None

    # 2. Unknown category string does not crash
    c_unknown = ClauseResponse(
        type="Arbitrary",
        text="Arbitrary clause text.",
        explanation="Explanation.",
        severity="LOW",
        clause_category="Custom Non Standard Provision",
    )
    assert c_unknown.clause_category == "Custom Non Standard Provision"

    # 3. Missing required field raises ValidationError
    with pytest.raises(ValidationError):
        ClauseResponse(
            text="Missing type, explanation, and severity.",
            clause_category=ClauseCategory.NON_COMPETE,
        )


def test_analysis_detail_response_contains_cuad_clauses():
    """
    Verify full AnalysisDetailResponse can serialize and deserialize clauses with CUAD categories.
    """
    analysis = AnalysisDetailResponse(
        safety_score=85,
        risk_level="LOW",
        summary="Mutual commercial agreement.",
        clauses=[
            ClauseResponse(
                type="Cap on Liability",
                text="Liability capped at 12 months fees.",
                explanation="Standard liability cap.",
                severity="LOW",
                clause_category=ClauseCategory.CAP_ON_LIABILITY,
            ),
            ClauseResponse(
                type="Non-Compete",
                text="Employee shall not engage in competing business for 2 years.",
                explanation="Post-employment non-compete.",
                severity="HIGH",
                clause_category=ClauseCategory.NON_COMPETE,
            ),
        ],
        citations=[],
        recommendations=["Review non-compete duration under local law."],
    )

    assert len(analysis.clauses) == 2
    assert analysis.clauses[0].clause_category == ClauseCategory.CAP_ON_LIABILITY
    assert analysis.clauses[1].clause_category == ClauseCategory.NON_COMPETE

    dumped = analysis.model_dump()
    assert dumped["clauses"][0]["clause_category"] == "Cap On Liability"
    assert dumped["clauses"][1]["clause_category"] == "Non-Compete"


def test_llm_service_cuad_prompt_coverage():
    """
    Verify LLMService prompt explicitly references all 41 CUAD categories.
    """
    assert len(CUAD_CLAUSE_CATEGORIES) == 41
    for expected in EXPECTED_41_CUAD_CATEGORIES:
        assert expected in CUAD_CATEGORIES_FORMATTED

    service = LLMService()
    fallback_result = service._rule_based_fallback("Governing Law: Laws of New York.\nLimitation of Liability: Capped.")
    assert "clauses" in fallback_result
    assert len(fallback_result["clauses"]) > 0

    # Ensure fallback clauses have valid CUAD clause_category
    for clause in fallback_result["clauses"]:
        assert "clause_category" in clause
        assert clause["clause_category"] in CUAD_CLAUSE_CATEGORIES

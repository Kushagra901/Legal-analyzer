"""
Compliance Service.
Performs rules audit checks against company templates.
"""
from app.services.llm_service import LLMService


class ComplianceService:
    """
    Service class responsible for managing rule-set matching logic.
    """

    def check_compliance(self, text: str, rule_set: str) -> dict[str, str | list[str]]:
        """
        Validates text against configured policies.
        Performs rule-set compliance checks for a standard NDA.

        Args:
            text (str): Contract raw text input.
            rule_set (str): Target rule-set catalog ID.

        Returns:
            dict[str, str | list[str]]: Compliance audit outcome status.
        """
        rule_set = rule_set or "standard_nda"
        violations = []

        # Try performing LLM-based compliance audit if API key is configured
        llm_service = LLMService()
        if llm_service.api_key:
            try:
                violations = llm_service.analyze_compliance(text, rule_set)
                status = "compliant" if not violations else "non-compliant"
                return {
                    "rule_set": rule_set,
                    "status": status,
                    "violations": violations
                }
            except Exception as e:
                # Log error and proceed to local fallback check
                import logging
                logging.getLogger(__name__).warning(
                    f"LLM compliance check failed, falling back to rule-based: {e}"
                )

        # Standard NDA policy checks (rule-based local fallback)
        text_lower = text.lower()

        # 1. Confidentiality Scope
        if "confidential" not in text_lower and "disclosure" not in text_lower:
            violations.append("Missing Confidentiality Obligations: The agreement does not contain standard confidentiality language.")

        # 2. Term Length (checking for duration or term references)
        term_keywords = ["term", "duration", "period", "years", "months", "survive", "surviving", "expiration", "terminate", "termination"]
        has_term = any(kw in text_lower for kw in term_keywords)
        if not has_term:
            violations.append("Missing Confidentiality Term: The agreement does not specify a duration or term for the confidentiality obligations.")

        # 3. Governing Law Present
        gov_keywords = ["governing law", "jurisdiction", "applicable law", "courts of", "governed by"]
        has_gov = any(kw in text_lower for kw in gov_keywords)
        if not has_gov:
            violations.append("Missing Governing Law or Jurisdiction: The agreement does not define applicable governing law.")

        # 4. Indemnification Warning (standard warning/risk for NDAs)
        if "indemnity" in text_lower or "indemnify" in text_lower or "hold harmless" in text_lower:
            violations.append("Indemnification Provision Detected: NDAs typically should not contain complex indemnification requirements.")

        status = "compliant" if not violations else "non-compliant"
        return {
            "rule_set": rule_set,
            "status": status,
            "violations": violations
        }



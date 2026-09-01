"""
Compliance Service.
Performs rules audit checks against company templates and auto-detects rule-sets.
"""
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service class responsible for managing rule-set matching and compliance checking logic.
    """

    def detect_rule_set(self, text: str, filename: str = "") -> str:
        """
        Auto-detects the most suitable rule-set catalog ID based on document text and filename.
        """
        import re
        text_lower = text.lower()
        fn_lower = filename.lower()
        combined = f"{fn_lower} {text_lower}"

        if re.search(r'\bnda\b', combined) or any(k in combined for k in ["non-disclosure", "nondisclosure", "confidentiality agreement", "confidential information"]):
            return "standard_nda"
        if re.search(r'\bdpa\b|\bgdpr\b', combined) or any(k in combined for k in ["data processing", "privacy policy", "personal data", "data controller"]):
            return "gdpr_privacy"
        if any(k in combined for k in ["franchise", "franchisor", "franchisee"]):
            return "franchise_agreement"
        if any(k in combined for k in ["lease", "landlord", "tenant", "tenancy", "premises"]):
            return "commercial_lease"
        if any(k in combined for k in ["employment", "employee", "offer letter", "consultant agreement", "independent contractor"]):
            return "employment_agreement"
        if re.search(r'\bsaas\b|\bsla\b', combined) or any(k in combined for k in ["software as a service", "master services", "service level agreement"]):
            return "saas_service_agreement"

        return "standard_nda"


    def check_compliance(self, text: str, rule_set: str | None = None) -> dict[str, str | list[str]]:
        """
        Validates text against configured policies.
        Performs rule-set compliance checks with LLM 3-tier fallback to local rule-based checking.

        Args:
            text (str): Contract raw text input.
            rule_set (str): Target rule-set catalog ID.

        Returns:
            dict[str, str | list[str]]: Compliance audit outcome status and violations.
        """
        rule_set = rule_set or "standard_nda"
        llm_service = LLMService()

        # Try performing LLM-based compliance audit if API key is configured
        effective_key = llm_service.gemini_api_key or llm_service.api_key or llm_service.anthropic_api_key
        if effective_key:
            try:
                violations = llm_service.analyze_compliance(text, rule_set)
                status = "compliant" if not violations else "non-compliant"
                return {
                    "rule_set": rule_set,
                    "status": status,
                    "violations": violations
                }
            except Exception as e:
                logger.warning(
                    f"LLM compliance check failed, falling back to rule-based: {e}"
                )

        # Local rule-based fallback
        violations = llm_service._rule_based_compliance_fallback(text, rule_set)
        status = "compliant" if not violations else "non-compliant"
        return {
            "rule_set": rule_set,
            "status": status,
            "violations": violations
        }

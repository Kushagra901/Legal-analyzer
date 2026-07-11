"""
Compliance Service.
Performs rules audit checks against company templates.
"""


class ComplianceService:
    """
    Service class responsible for managing rule-set matching logic.
    """

    def check_compliance(self, text: str, rule_set: str) -> dict[str, str | list[str]]:
        """
        Validates text against configured policies.
        Performs basic keyword audit checks for a standard NDA.

        Args:
            text (str): Contract raw text input.
            rule_set (str): Target rule-set catalog ID.

        Returns:
            dict[str, str | list[str]]: Compliance audit outcome status.
        """
        violations = []
        rule_set = rule_set or "standard_nda"
        text_lower = text.lower()
        
        # Standard NDA policy checks
        if "confidential" not in text_lower and "disclosure" not in text_lower:
            violations.append("Missing Confidentiality Obligations: The agreement does not contain standard confidentiality language.")
            
        if "governing law" not in text_lower and "jurisdiction" not in text_lower:
            violations.append("Missing Governing Law or Jurisdiction: The agreement does not define applicable governing law.")
            
        if "indemnity" in text_lower or "indemnify" in text_lower:
            violations.append("Indemnification Provision Detected: NDAs typically should not contain complex indemnification requirements.")
            
        status = "compliant" if not violations else "non-compliant"
        return {
            "rule_set": rule_set,
            "status": status,
            "violations": violations
        }


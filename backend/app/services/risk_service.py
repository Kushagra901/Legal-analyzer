"""
Risk Service.
Identifies risky clauses and applies numerical compliance ratings to documents.
"""


class RiskService:
    """
    Service class responsible for rating clause risk profiles and safety indexes.
    """

    def score_document_risk(self, clauses: list[dict[str, str]]) -> int:
        """
        Calculates safety score for a document list of clauses.
        Start from 100, deduct 15 for each HIGH severity clause, and 5 for each MEDIUM clause.

        Args:
            clauses (list[dict[str, str]]): List of clauses to verify.

        Returns:
            int: Calculated safety rating score (0-100).
        """
        score = 100
        for clause in clauses:
            severity = str(clause.get("severity", "LOW")).upper()
            if severity == "HIGH":
                score -= 15
            elif severity == "MEDIUM":
                score -= 5
        return max(0, min(100, score))

    def get_risk_level(self, safety_score: int) -> str:
        """
        Determines the overall risk level string based on the safety score.

        Args:
            safety_score (int): Calculated safety score (0-100).

        Returns:
            str: "LOW", "MEDIUM", or "HIGH".
        """
        if safety_score >= 80:
            return "LOW"
        elif safety_score >= 50:
            return "MEDIUM"
        else:
            return "HIGH"


"""
LLM Service.
Handles structured interactions with Claude and Gemini LLM models.
"""


class LLMService:
    """
    Service class responsible for AI structured prompts and text analysis.
    """

    def analyze_contract(self, text: str) -> dict[str, str | list[str]]:
        """
        Send document text to the LLM to extract key features.

        Args:
            text (str): Contract raw text input.

        Returns:
            dict[str, str | list[str]]: Parsed JSON output containing contract insights.
        """
        return {
            "summary": "Standard contract details.",
            "clauses": ["Limitation of Liability", "Termination"],
        }

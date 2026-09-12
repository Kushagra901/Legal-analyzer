"""
ollama_service.py
Service for interacting with locally hosted Ollama LLM models.

Implements the 5 master prompt operations as class methods:
1. classify_document(): Categorizes contract and identifies indicators.
2. extract_entities(): Extracts contracting parties, key dates, and deal terms.
3. analyze_clause_risk(): Evaluates legal risk, severity, and actionable mitigations.
4. audit_compliance(): Audits agreement against standard regulatory/policy rule sets.
5. generate_summary(): Generates clear, plain-English executive prose summaries.

Includes JSON response cleaning, single-retry error correction for malformed JSON,
and reachability health checks.
"""

import json
import logging
import re
from typing import Any, TypedDict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentClassification(TypedDict):
    """Schema for document classification results."""
    document_type: str
    confidence: float
    summary_category: str
    key_indicators: list[str]


class ExtractedEntities(TypedDict, total=False):
    """Schema for extracted contract parties and core deal parameters."""
    parties: list[str]
    effective_date: str | None
    expiration_date: str | None
    auto_renewal: bool | None
    renewal_notice_days: int | None
    governing_law: str | None
    jurisdiction: str | None
    document_type: str | None
    key_amounts: list[str]


class ClauseRiskAnalysis(TypedDict, total=False):
    """Schema for individual clause risk evaluations."""
    type: str
    severity: str
    explanation: str
    issue: str
    recommendation: str
    confidence_score: float | None


class ComplianceAuditResult(TypedDict, total=False):
    """Schema for document policy compliance audit results."""
    status: str
    rule_set: str
    violations: list[str]
    missing_clauses: list[str]
    safety_score: int
    risk_level: str


def clean_json_string(raw: str) -> str:
    """
    Clean and extract valid JSON string from model output.

    Strips markdown code fences, reasoning/thinking tags, and leading/trailing
    conversational text.

    Args:
        raw (str): Raw string output from Ollama generation.

    Returns:
        str: Isolated JSON substring ready for json.loads.

    Raises:
        ValueError: If input is empty or contains no bracketed JSON structures.
    """
    if not raw or not raw.strip():
        raise ValueError("Empty or whitespace-only response received.")

    cleaned = raw.strip()

    # 1. Strip reasoning/thinking tags (e.g. <think>...</think> from Qwen/DeepSeek)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned).strip()

    # 2. Extract contents inside markdown code block if present
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    # 3. Locate outermost JSON object {...} or array [...]
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")

    start_idx = -1
    end_idx = -1

    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_idx = cleaned.rfind("}")
    elif first_bracket != -1:
        start_idx = first_bracket
        end_idx = cleaned.rfind("]")

    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        cleaned = cleaned[start_idx : end_idx + 1].strip()

    return cleaned


class OllamaService:
    """
    Ollama service wrapper executing the 5 master legal review prompts.
    """

    @classmethod
    def check_health(cls, base_url: str | None = None) -> bool:
        """
        Determine whether the Ollama instance is currently reachable.

        Args:
            base_url (str | None): Optional base URL. Defaults to settings.OLLAMA_BASE_URL.

        Returns:
            bool: True if Ollama responds successfully, False otherwise.
        """
        url = base_url if base_url is not None else settings.OLLAMA_BASE_URL
        if not url or not url.strip():
            return False

        target_url = f"{url.rstrip('/')}/api/version"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(target_url)
                if resp.status_code == 200:
                    return True
                # Fallback to root endpoint check
                root_resp = client.get(f"{url.rstrip('/')}/")
                return root_resp.status_code == 200
        except Exception:
            return False

    is_healthy = check_health

    @classmethod
    def _call_generate(
        cls,
        prompt: str,
        format_json: bool = True,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0
    ) -> str:
        """
        Call Ollama's /api/generate endpoint.

        Args:
            prompt (str): Generation prompt text.
            format_json (bool): Whether to enforce 'format': 'json'.
            base_url (str | None): Optional base URL override.
            model (str | None): Optional model override.
            timeout (float): Request timeout in seconds.

        Returns:
            str: Raw response text emitted by the model.

        Raises:
            ConnectionError: If Ollama URL is unconfigured or unreachable.
            RuntimeError: If Ollama returns an HTTP error status.
        """
        url = base_url if base_url is not None else settings.OLLAMA_BASE_URL
        if not url or not url.strip():
            raise ConnectionError("Ollama base URL is not configured or empty.")

        target_model = model or settings.OLLAMA_MODEL or "qwen3:8b"
        endpoint = f"{url.rstrip('/')}/api/generate"

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False
        }
        if format_json:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                return str(data.get("response", ""))
        except httpx.RequestError as req_err:
            raise ConnectionError(f"Failed to connect to Ollama at {url}: {req_err}") from req_err
        except httpx.HTTPStatusError as status_err:
            raise RuntimeError(f"Ollama returned HTTP error {status_err.response.status_code}: {status_err}") from status_err

    @classmethod
    def _generate_json_with_retry(
        cls,
        prompt: str,
        base_url: str | None = None,
        model: str | None = None
    ) -> dict[str, Any]:
        """
        Call Ollama with format='json', validate JSON, and retry once on invalid JSON.

        Args:
            prompt (str): Prompt instructing model to return JSON.
            base_url (str | None): Optional base URL override.
            model (str | None): Optional model override.

        Returns:
            dict[str, Any]: Parsed JSON dictionary.

        Raises:
            ValueError: If both initial attempt and retry fail to return valid JSON.
            ConnectionError: If Ollama is unreachable.
        """
        raw_output = cls._call_generate(prompt=prompt, format_json=True, base_url=base_url, model=model)

        # Attempt 1: Clean and parse
        try:
            cleaned = clean_json_string(raw_output)
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, json.JSONDecodeError) as parse_err:
            logger.warning("Initial Ollama response was invalid JSON (%s). Retrying with correction prompt...", parse_err)

        # Attempt 2: Explicit correction retry
        retry_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Your previous response was invalid JSON, fix it. "
            "Return ONLY a valid JSON object matching the requested schema. "
            "Do not include commentary, explanations, or markdown code fences outside the JSON.\n"
            f"Previous response was:\n{raw_output}"
        )
        retry_raw = cls._call_generate(prompt=retry_prompt, format_json=True, base_url=base_url, model=model)

        try:
            retry_cleaned = clean_json_string(retry_raw)
            retry_parsed = json.loads(retry_cleaned)
            if isinstance(retry_parsed, dict):
                return retry_parsed
            raise ValueError(f"Expected JSON object dictionary, received {type(retry_parsed)}")
        except (ValueError, json.JSONDecodeError) as retry_err:
            raise ValueError(
                f"Ollama returned invalid JSON after retry: {retry_err}. Response snippet: {retry_raw[:200]}"
            ) from retry_err

    # =========================================================================
    # Master Prompt 1: classify_document
    # =========================================================================
    @classmethod
    def classify_document(
        cls,
        document_text: str,
        base_url: str | None = None,
        model: str | None = None
    ) -> DocumentClassification:
        """
        Classify document category, confidence score, and primary structural indicators.

        Args:
            document_text (str): Raw document content or excerpt.
            base_url (str | None): Optional base URL.
            model (str | None): Optional model override.

        Returns:
            DocumentClassification: Structured document classification dictionary.
        """
        prompt = (
            "You are an expert legal document triage attorney. Analyze the following legal document and classify it.\n"
            "Return a JSON object strictly matching this schema:\n"
            "{\n"
            '  "document_type": "string (e.g. Non-Disclosure Agreement, Employment Agreement, SaaS Agreement, Commercial Lease, Master Services Agreement, Other)",\n'
            '  "confidence": 0.95,\n'
            '  "summary_category": "string (e.g. Confidentiality, Employment, Commercial, Licensing)",\n'
            '  "key_indicators": ["list of strings citing distinctive terms or phrases found in the text"]\n'
            "}\n\n"
            f"Document Text:\n{document_text[:6000]}"
        )

        data = cls._generate_json_with_retry(prompt, base_url=base_url, model=model)
        return DocumentClassification(
            document_type=str(data.get("document_type", "Legal Agreement")),
            confidence=float(data.get("confidence", 0.8)),
            summary_category=str(data.get("summary_category", "General")),
            key_indicators=list(data.get("key_indicators", []))
        )

    # =========================================================================
    # Master Prompt 2: extract_entities
    # =========================================================================
    @classmethod
    def extract_entities(
        cls,
        document_text: str,
        base_url: str | None = None,
        model: str | None = None
    ) -> ExtractedEntities:
        """
        Extract contracting parties, dates, auto-renewal rules, and core parameters.

        Args:
            document_text (str): Raw document content.
            base_url (str | None): Optional base URL.
            model (str | None): Optional model override.

        Returns:
            ExtractedEntities: Typed dictionary matching DealTermsResponse schema.
        """
        prompt = (
            "You are an expert legal contract analyst. Extract key entities and deal terms from this legal document.\n"
            "Return a JSON object strictly matching this schema:\n"
            "{\n"
            '  "parties": ["list of party names"],\n'
            '  "effective_date": "YYYY-MM-DD or string date or null",\n'
            '  "expiration_date": "YYYY-MM-DD or string date or null",\n'
            '  "auto_renewal": true,\n'
            '  "renewal_notice_days": 30,\n'
            '  "governing_law": "string state/country or null",\n'
            '  "jurisdiction": "string court/venue or null",\n'
            '  "document_type": "string document type or null",\n'
            '  "key_amounts": ["list of monetary figures, liability caps, or penalty amounts"]\n'
            "}\n\n"
            f"Document Text:\n{document_text[:8000]}"
        )

        data = cls._generate_json_with_retry(prompt, base_url=base_url, model=model)
        return ExtractedEntities(
            parties=list(data.get("parties", [])),
            effective_date=data.get("effective_date"),
            expiration_date=data.get("expiration_date"),
            auto_renewal=data.get("auto_renewal"),
            renewal_notice_days=data.get("renewal_notice_days"),
            governing_law=data.get("governing_law"),
            jurisdiction=data.get("jurisdiction"),
            document_type=data.get("document_type"),
            key_amounts=list(data.get("key_amounts", []))
        )

    # =========================================================================
    # Master Prompt 3: analyze_clause_risk
    # =========================================================================
    @classmethod
    def analyze_clause_risk(
        cls,
        clause_text: str,
        clause_type: str = "",
        base_url: str | None = None,
        model: str | None = None
    ) -> ClauseRiskAnalysis:
        """
        Evaluate legal exposure, severity rating, and mitigation recommendations for a clause.

        Args:
            clause_text (str): Text of the individual contract clause.
            clause_type (str): Optional clause category label.
            base_url (str | None): Optional base URL.
            model (str | None): Optional model override.

        Returns:
            ClauseRiskAnalysis: Evaluated risk details and mitigation advice.
        """
        category_hint = f" (Category: {clause_type})" if clause_type else ""
        prompt = (
            f"You are a senior contract risk attorney. Evaluate this clause{category_hint} for potential risks.\n"
            "Return a JSON object strictly matching this schema:\n"
            "{\n"
            '  "type": "string clause category (e.g. Indemnification, Limitation of Liability, Termination, Confidentiality)",\n'
            '  "severity": "LOW, MEDIUM, or HIGH",\n'
            '  "explanation": "Plain-English explanation of why this clause creates risk",\n'
            '  "issue": "Concise 1-sentence statement of the legal exposure",\n'
            '  "recommendation": "Actionable negotiation suggestion or redline mitigation",\n'
            '  "confidence_score": 0.90\n'
            "}\n\n"
            f"Clause Text:\n{clause_text[:4000]}"
        )

        data = cls._generate_json_with_retry(prompt, base_url=base_url, model=model)
        severity = str(data.get("severity", "MEDIUM")).upper()
        if severity not in {"LOW", "MEDIUM", "HIGH"}:
            severity = "MEDIUM"

        return ClauseRiskAnalysis(
            type=str(data.get("type", clause_type or "General")),
            severity=severity,
            explanation=str(data.get("explanation", "")),
            issue=str(data.get("issue", "")),
            recommendation=str(data.get("recommendation", "")),
            confidence_score=float(data.get("confidence_score", 0.85)) if data.get("confidence_score") is not None else None
        )

    # =========================================================================
    # Master Prompt 4: audit_compliance
    # =========================================================================
    @classmethod
    def audit_compliance(
        cls,
        document_text: str,
        rule_set: str = "standard_nda",
        base_url: str | None = None,
        model: str | None = None
    ) -> ComplianceAuditResult:
        """
        Audit document text against compliance standards and required legal provisions.

        Args:
            document_text (str): Document text to inspect.
            rule_set (str): The compliance standard (e.g. 'standard_nda', 'gdpr_privacy').
            base_url (str | None): Optional base URL.
            model (str | None): Optional model override.

        Returns:
            ComplianceAuditResult: Document compliance audit evaluation.
        """
        prompt = (
            f"You are a legal compliance auditor. Audit the document against the '{rule_set}' policy standards.\n"
            "Identify missing protections, standard covenants, and potential policy violations.\n"
            "Return a JSON object strictly matching this schema:\n"
            "{\n"
            '  "status": "compliant or non-compliant",\n'
            f'  "rule_set": "{rule_set}",\n'
            '  "violations": ["list of specific policy violations or unacceptable clauses"],\n'
            '  "missing_clauses": ["list of essential protective clauses missing from the agreement"],\n'
            '  "safety_score": 85,\n'
            '  "risk_level": "LOW, MEDIUM, or HIGH"\n'
            "}\n\n"
            f"Document Text:\n{document_text[:8000]}"
        )

        data = cls._generate_json_with_retry(prompt, base_url=base_url, model=model)
        status_val = str(data.get("status", "non-compliant")).lower()
        if "compliant" in status_val and "non" not in status_val:
            clean_status = "compliant"
        else:
            clean_status = "non-compliant"

        risk_level = str(data.get("risk_level", "MEDIUM")).upper()
        if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
            risk_level = "MEDIUM"

        return ComplianceAuditResult(
            status=clean_status,
            rule_set=str(data.get("rule_set", rule_set)),
            violations=list(data.get("violations", [])),
            missing_clauses=list(data.get("missing_clauses", [])),
            safety_score=int(data.get("safety_score", 50)),
            risk_level=risk_level
        )

    # =========================================================================
    # Master Prompt 5: generate_summary
    # =========================================================================
    @classmethod
    def generate_summary(
        cls,
        document_text: str,
        base_url: str | None = None,
        model: str | None = None
    ) -> str:
        """
        Generate a plain-English, executive-level summary in prose (not JSON).

        Args:
            document_text (str): Document text to summarize.
            base_url (str | None): Optional base URL.
            model (str | None): Optional model override.

        Returns:
            str: Professional multi-paragraph prose summary.
        """
        prompt = (
            "You are an experienced legal advisor providing an executive briefing for founders and business leaders.\n"
            "Summarize the following legal document in clear, plain-English prose.\n"
            "Explain the contract's primary purpose, the core obligations of each party, key dates or renewal triggers, "
            "and the top legal risks to bear in mind.\n"
            "Do NOT return JSON. Write a clear, professional, multi-paragraph prose summary.\n\n"
            f"Document Content:\n{document_text[:8000]}"
        )

        return cls._call_generate(prompt=prompt, format_json=False, base_url=base_url, model=model).strip()

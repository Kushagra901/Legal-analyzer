"""
Compliance Service.
Performs rules audit checks against company templates and auto-detects rule-sets.
"""
import json
import logging
import uuid
from typing import Any

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


    def check_compliance(
        self,
        text: str | uuid.UUID,
        rule_set: str | None = None,
        db: Any = None
    ) -> dict[str, Any]:
        """
        Validates text or document against configured policies.
        If a document UUID is passed, auto-detects rule set if not provided,
        runs compliance audit, persists ComplianceCheck record to PostgreSQL, and returns outcome.

        Args:
            text: Contract raw text input or document UUID.
            rule_set: Target rule-set catalog ID.
            db: Optional active SQLAlchemy session.

        Returns:
            dict[str, Any]: Compliance audit outcome status and violations.
        """
        is_uuid = False
        doc_uuid = None
        try:
            if isinstance(text, uuid.UUID):
                is_uuid = True
                doc_uuid = text
            elif isinstance(text, str):
                clean_str = text.strip()
                if len(clean_str) in (32, 36) and not (" " in clean_str or "\n" in clean_str):
                    doc_uuid = uuid.UUID(clean_str)
                    is_uuid = True
        except (ValueError, AttributeError):
            is_uuid = False

        if is_uuid and doc_uuid:
            from app.core.database import SessionLocal
            from app.models import ComplianceCheck, Document, ExtractedText

            session = db or SessionLocal()
            should_close = db is None
            try:
                doc = session.query(Document).filter(Document.id == doc_uuid).first()
                extracted_obj = session.query(ExtractedText).filter(ExtractedText.document_id == doc_uuid).first()
                raw_text = extracted_obj.content if (extracted_obj and extracted_obj.content) else ""
                if not raw_text and doc:
                    raw_text = getattr(doc, "original_text", "") or getattr(doc, "extracted_text", "")
                if not raw_text:
                    raw_text = "Sample contract text."

                if not rule_set:
                    rule_set = self.detect_rule_set(raw_text, doc.filename if doc else "")

                res = self.check_compliance(raw_text, rule_set=rule_set)
                violations = res.get("violations", [])

                if doc:
                    session.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).delete()
                    db_compliance = ComplianceCheck(
                        id=uuid.uuid4(),
                        document_id=doc.id,
                        rule_set=rule_set,
                        result=json.dumps(violations)
                    )
                    session.add(db_compliance)
                    session.commit()

                return res
            finally:
                if should_close:
                    session.close()

        rule_set = rule_set or "standard_nda"
        llm_service = LLMService()

        # Try performing LLM-based compliance audit if API key is configured
        effective_key = llm_service.gemini_api_key or llm_service.api_key or llm_service.anthropic_api_key
        if effective_key:
            try:
                violations = llm_service.analyze_compliance(str(text), rule_set)
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
        violations = llm_service._rule_based_compliance_fallback(str(text), rule_set)
        status = "compliant" if not violations else "non-compliant"
        return {
            "rule_set": rule_set,
            "status": status,
            "violations": violations
        }

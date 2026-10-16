"""
Celery asynchronous background tasks for document analysis.
"""

import json
import logging
import uuid

from app.core.database import SessionLocal
from app.models import (
    AuditLog,
    Clause,
    ComplianceCheck,
    Document,
    ExtractedText,
    LegalReference,
    RiskFlag,
)
from app.services.compliance_service import ComplianceService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.risk_service import RiskService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def execute_document_analysis(document_id: str):
    """
    Core function that performs document analysis, saving clauses, risk flags,
    compliance checks, and legal citations to PostgreSQL.
    """
    db = SessionLocal()
    try:
        doc_uuid = uuid.UUID(document_id)
        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc:
            logger.error("Task error: Document %s not found.", document_id)
            return

        doc.status = "processing"
        db.commit()

        extracted = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
        extracted_text = extracted.content if extracted else ""

        llm_service = LLMService()
        risk_service = RiskService()
        compliance_service = ComplianceService()

        # Run AI analysis
        analysis = llm_service.analyze_contract(extracted_text)

        # Calculate scores
        safety_score = risk_service.score_document_risk(analysis.get("clauses", []))
        risk_level = risk_service.get_risk_level(safety_score)

        # Run compliance audit
        compliance_res = compliance_service.check_compliance(extracted_text, "standard_nda")

        # Save clauses and risk flags
        for clause_data in analysis.get("clauses", []):
            if isinstance(clause_data, str):
                clause_data = {
                    "clause_type": "General",
                    "clause_text": clause_data,
                    "category": "General",
                    "confidence_score": 0.9,
                    "severity": "LOW",
                    "explanation": ""
                }
            elif not isinstance(clause_data, dict):
                continue

            confidence_val = clause_data.get("confidence_score")
            confidence_float = float(confidence_val) if confidence_val is not None else 0.95
            db_clause = Clause(
                id=uuid.uuid4(),
                document_id=doc.id,
                clause_type=clause_data.get("clause_type"),
                clause_text=clause_data.get("clause_text"),
                category=clause_data.get("category", "General"),
                confidence_score=confidence_float,
            )
            db.add(db_clause)
            db.flush()

            severity = clause_data.get("severity", "LOW")
            explanation = clause_data.get("explanation", "")
            if severity in ("MEDIUM", "HIGH") or explanation:
                db_flag = RiskFlag(
                    id=uuid.uuid4(),
                    clause_id=db_clause.id,
                    severity=severity,
                    explanation=explanation
                )
                db.add(db_flag)

        # Save compliance audit record
        compliance_rule_set = "standard_nda"
        compliance_violations = []
        if isinstance(compliance_res, dict):
            compliance_rule_set = compliance_res.get("rule_set", "standard_nda")
            compliance_violations = compliance_res.get("violations", [])
        elif isinstance(compliance_res, list):
            compliance_violations = compliance_res

        db_compliance = ComplianceCheck(
            id=uuid.uuid4(),
            document_id=doc.id,
            rule_set=compliance_rule_set,
            result=json.dumps(compliance_violations)
        )
        db.add(db_compliance)

        # Save legal references
        for citation_data in analysis.get("citations", []):
            if isinstance(citation_data, str):
                source = "Legal Citation"
                citation = citation_data
            elif isinstance(citation_data, dict):
                source = citation_data.get("source", "Legal Citation")
                citation = citation_data.get("citation", str(citation_data))
            else:
                continue

            db_ref = LegalReference(
                id=uuid.uuid4(),
                document_id=doc.id,
                source=source,
                citation=citation
            )
            db.add(db_ref)

        # Update Document record
        doc.summary = analysis.get("summary", "")
        doc.document_overview = analysis.get("document_overview")
        doc.parties = analysis.get("parties")
        doc.key_dates = analysis.get("key_dates")
        doc.missing_sections = analysis.get("missing_sections")
        doc.plain_english_summary = analysis.get("plain_english_summary")
        doc.safety_score = safety_score
        doc.risk_level = risk_level
        doc.status = "completed"
        db.commit()

        # Run text chunking and 768-dim vector embedding generation once per document
        embedding_service = EmbeddingService()
        try:
            embedding_service.chunk_and_embed_document(doc.id, extracted_text, db)
        except Exception as e:
            logger.warning("Chunking and embedding failed in background task for %s: %s", document_id, e)

        # Write audit log
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"Asynchronous document analysis completed: {doc.filename} (Safety Score: {doc.safety_score}, Risk Level: {doc.risk_level})"
        )
        db.add(audit_log)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error("Error in analyze_document_task for %s: %s", document_id, e)
        doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc:
            doc.status = "failed"
            doc.summary = f"Analysis failure: {str(e)}"
            db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.analyze_document_task", bind=True)
def analyze_document_task(self, document_id: str):
    """
    Celery task wrapper for analyze_document_task.
    """
    execute_document_analysis(document_id)

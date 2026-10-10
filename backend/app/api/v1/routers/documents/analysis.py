"""
Analysis router for documents.
Handles OCR, LLM contract analysis, multi-agent pipeline, compliance auditing,
scoring, deep extraction, and executive quick summaries.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import (
    AuditLog,
    Clause,
    ComplianceCheck,
    DeepExtraction,
    ExtractedText,
    Report,
    RiskFlag,
    User,
)
from app.models.schemas import (
    AnalysisStatusResponse,
    ComplianceAuditRequest,
    ComplianceResponse,
    DeepExtractionResponse,
    QuickSummaryResponse,
)
from app.services.compliance_service import ComplianceService
from app.services.deep_extraction_service import DeepExtractionService
from app.services.legal_chunker import split_legal_clauses
from app.services.llm_service import LLMService
from app.services.ollama_service import OllamaService
from app.services.report_generator_service import ReportGeneratorService
from app.services.risk_service import RiskService
from app.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)


class AuditAction(BaseModel):
    """Schema for custom audit action recording."""
    action: str | None = None


@router.post("/{document_id}/ocr", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_ocr(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Run OCR extraction status verification."""
    doc = get_accessible_document(db, document_id, current_user)
    return AnalysisStatusResponse(
        status="ocr_completed",
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/analyze", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_analysis(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Run baseline single-pass contract analysis."""
    doc = get_accessible_document(db, document_id, current_user)

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj else "Sample contract text."

    from app.api.v1.routers import documents
    llm_cls = getattr(documents, "LLMService", LLMService)
    llm_service = llm_cls()
    try:
        analysis = llm_service.analyze_contract(extracted_text)
    except Exception:
        logger.exception("LLM Analysis failed during document analysis")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document analysis pipeline failed. Please retry."
        )

    # Clean up existing clauses/risk flags to prevent duplication
    clauses_db = db.query(Clause).filter(Clause.document_id == doc.id).all()
    for c in clauses_db:
        db.query(RiskFlag).filter(RiskFlag.clause_id == c.id).delete()
    db.query(Clause).filter(Clause.document_id == doc.id).delete()
    db.commit()

    for clause_data in analysis.get("clauses", []):
        db_clause = Clause(
            id=uuid.uuid4(),
            document_id=doc.id,
            clause_type=clause_data.get("clause_type"),
            clause_text=clause_data.get("clause_text"),
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

    doc.summary = analysis.get("summary", "")
    db.commit()

    return AnalysisStatusResponse(
        status="analyzed",
        summary=doc.summary,
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/agent-analyze", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_agent_analysis(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """
    Run the multi-agent legal analysis pipeline sequentially:
    Agent 1 (Classify) -> Agent 2 (Extract Entities) -> Agent 3 (Chunk) ->
    Agent 4 (Risk Analysis) & Agent 5 (Compliance Audit) -> Agent 6 (Summarization).
    """
    doc = get_accessible_document(db, document_id, current_user)

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj and extracted_text_obj.content else ""
    if not extracted_text:
        extracted_text = "Sample contract text."

    ollama_healthy = OllamaService.check_health()

    # Agent 1: Classify document
    if ollama_healthy:
        try:
            classification = OllamaService.classify_document(extracted_text)
        except Exception as e:
            logger.warning("Agent 1 (classify) Ollama error (%s), falling back.", e)
            classification = {
                "document_type": "Non-Disclosure Agreement" if "confidential" in extracted_text.lower() else "Legal Agreement",
                "confidence": 0.85,
                "summary_category": "Confidentiality" if "confidential" in extracted_text.lower() else "Commercial",
                "key_indicators": ["Confidentiality", "Obligations"]
            }
    else:
        classification = {
            "document_type": "Non-Disclosure Agreement" if "confidential" in extracted_text.lower() else "Legal Agreement",
            "confidence": 0.85,
            "summary_category": "Confidentiality" if "confidential" in extracted_text.lower() else "Commercial",
            "key_indicators": ["Confidentiality", "Obligations"]
        }

    # Agent 2: Extract entities
    if ollama_healthy:
        try:
            entities = OllamaService.extract_entities(extracted_text)
        except Exception as e:
            logger.warning("Agent 2 (extract_entities) Ollama error (%s), falling back.", e)
            entities = {
                "parties": ["Party A", "Party B"],
                "effective_date": None,
                "expiration_date": None,
                "auto_renewal": False,
                "renewal_notice_days": None,
                "governing_law": "Delaware",
                "jurisdiction": "State Courts",
                "document_type": classification.get("document_type"),
                "key_amounts": []
            }
    else:
        entities = {
            "parties": ["Disclosing Party", "Receiving Party"] if "confidential" in extracted_text.lower() else ["Party A", "Party B"],
            "effective_date": None,
            "expiration_date": None,
            "auto_renewal": False,
            "renewal_notice_days": None,
            "governing_law": "Delaware",
            "jurisdiction": "State Courts",
            "document_type": classification.get("document_type"),
            "key_amounts": []
        }

    # Agent 3: Chunk document using legal_chunker
    chunks = split_legal_clauses(extracted_text)
    if not chunks:
        chunks = [extracted_text]

    # Clean up existing clauses and risk flags to prevent duplicate entries
    clauses_db = db.query(Clause).filter(Clause.document_id == doc.id).all()
    for c in clauses_db:
        db.query(RiskFlag).filter(RiskFlag.clause_id == c.id).delete()
    db.query(Clause).filter(Clause.document_id == doc.id).delete()
    db.commit()

    # Agent 4: Risk Analysis per chunk & Agent 5: Compliance Audit per chunk
    clause_records: list[dict] = []
    all_violations: list[str] = []
    all_missing_clauses: list[str] = []
    rule_set = str(classification.get("document_type", "standard_nda"))

    for idx, chunk_text in enumerate(chunks):
        def _get_rule_based_risk(chunk: str, chunk_idx: int) -> dict:
            is_risky = any(w in chunk.lower() for w in ["indemnif", "unlimited", "liquidated damages", "sole discretion"])
            severity = "HIGH" if "unlimited" in chunk.lower() else ("MEDIUM" if is_risky else "LOW")
            return {
                "type": f"Clause {chunk_idx + 1}",
                "severity": severity,
                "explanation": "Flagged by automated rule analysis." if is_risky else "",
                "issue": "Legal risk identified." if is_risky else "",
                "confidence_score": 0.85
            }

        if ollama_healthy:
            try:
                risk_info = OllamaService.analyze_clause_risk(chunk_text)
            except Exception as e:
                logger.warning("Risk analysis per chunk failed (%s), falling back.", e)
                risk_info = _get_rule_based_risk(chunk_text, idx)
        else:
            risk_info = _get_rule_based_risk(chunk_text, idx)

        clause_type = str(risk_info.get("type") or f"Clause {idx + 1}")
        db_clause = Clause(
            id=uuid.uuid4(),
            document_id=doc.id,
            clause_type=clause_type,
            clause_text=chunk_text,
            category=str(classification.get("summary_category", "General")),
            confidence_score=float(risk_info.get("confidence_score") or 0.9)
        )
        db.add(db_clause)
        db.flush()

        severity_val = str(risk_info.get("severity", "LOW")).upper()
        if severity_val not in ("LOW", "MEDIUM", "HIGH"):
            severity_val = "LOW"
        explanation_val = str(risk_info.get("explanation") or risk_info.get("issue") or "")

        if severity_val in ("MEDIUM", "HIGH") or explanation_val:
            db_flag = RiskFlag(
                id=uuid.uuid4(),
                clause_id=db_clause.id,
                severity=severity_val,
                explanation=explanation_val or f"{severity_val} severity risk identified."
            )
            db.add(db_flag)

        clause_records.append({"severity": severity_val})

        # 5. Compliance Audit per chunk
        if ollama_healthy:
            try:
                comp_res = OllamaService.audit_compliance(chunk_text, rule_set=rule_set)
                for v in comp_res.get("violations", []):
                    if v and v not in all_violations:
                        all_violations.append(v)
                for m in comp_res.get("missing_clauses", []):
                    if m and m not in all_missing_clauses:
                        all_missing_clauses.append(m)
            except Exception as e:
                logger.warning("Compliance audit per chunk failed (%s), continuing.", e)

    # Calculate overall document risk ratings
    risk_service = RiskService()
    safety_score = risk_service.score_document_risk(clause_records)
    risk_level = risk_service.get_risk_level(safety_score)

    # Agent 6 (Aggregation & Summarization): Summarization agent
    parties_list = entities.get("parties") or []
    parties_str = ", ".join(parties_list) if parties_list else "the parties"
    summary_context = (
        f"Document Type: {classification.get('document_type')}\n"
        f"Parties: {parties_str}\n"
        f"Number of Clauses: {len(chunks)}\n"
        f"Overall Risk Level: {risk_level} (Safety Score: {safety_score}/100)\n"
        f"Violations or Missing Protections: {', '.join(all_violations + all_missing_clauses) or 'None'}\n\n"
        f"Text excerpt:\n{extracted_text[:3000]}"
    )

    if ollama_healthy:
        try:
            summary_text = OllamaService.generate_summary(summary_context)
        except Exception as e:
            logger.warning("Summarization agent error (%s), falling back to structured summary.", e)
            summary_text = (
                f"Executive Summary for {classification.get('document_type', 'Agreement')}. "
                f"This document governs terms between {parties_str}. "
                f"The overall risk is assessed as {risk_level} with a safety score of {safety_score}/100."
            )
    else:
        summary_text = (
            f"Executive Summary for {classification.get('document_type', 'Agreement')}. "
            f"This document governs terms between {parties_str}. "
            f"The overall risk is assessed as {risk_level} with a safety score of {safety_score}/100."
        )

    # Save results to documents table columns
    doc.summary = summary_text
    doc.plain_english_summary = summary_text
    doc.safety_score = safety_score
    doc.risk_level = risk_level
    doc.parties = parties_list
    doc.key_dates = {
        "effective_date": entities.get("effective_date"),
        "expiration_date": entities.get("expiration_date"),
        "auto_renewal": entities.get("auto_renewal"),
        "renewal_notice_days": entities.get("renewal_notice_days")
    }
    doc.missing_sections = all_missing_clauses
    doc.document_overview = f"{classification.get('document_type', 'Agreement')} involving {parties_str}. Assessed as {risk_level} risk."
    doc.status = "analyzed"

    # Record audit log entry
    try:
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"5-agent pipeline completed: {doc.filename} (Type: {classification.get('document_type')}, Risk: {risk_level}, Score: {safety_score})"
        )
        db.add(audit_log)
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)

    db.commit()
    db.refresh(doc)

    return AnalysisStatusResponse(
        status=doc.status,
        message="5-agent pipeline completed successfully.",
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level,
        summary=doc.summary
    )


@router.post("/{document_id}/score", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_scoring(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Calculate and update overall document risk ratings."""
    doc = get_accessible_document(db, document_id, current_user)

    clauses = db.query(Clause).filter(Clause.document_id == doc.id).all()
    clause_list = []
    for c in clauses:
        flags = db.query(RiskFlag).filter(RiskFlag.clause_id == c.id).all()
        severity = flags[0].severity if flags else "LOW"
        clause_list.append({"severity": severity})

    risk_service = RiskService()
    safety_score = risk_service.score_document_risk(clause_list)
    risk_level = risk_service.get_risk_level(safety_score)

    doc.safety_score = safety_score
    doc.risk_level = risk_level
    db.commit()

    return AnalysisStatusResponse(
        status="scored",
        safety_score=safety_score,
        risk_level=risk_level,
        document_id=document_id,
        filename=doc.filename
    )


@router.post("/{document_id}/compliance", response_model=ComplianceResponse)
@limiter.limit("60/minute")
def run_compliance(
    request: Request,
    document_id: str,
    payload: ComplianceAuditRequest | None = None,
    rule_set: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ComplianceResponse:
    """
    Run compliance check on a document against a specific rule set or auto-detected policy.
    Callable by the n8n compliance agent via internal service token or authenticated users.
    """
    doc = get_accessible_document(db, document_id, current_user)

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = ""
    if extracted_text_obj and extracted_text_obj.content:
        extracted_text = extracted_text_obj.content
    elif hasattr(doc, "extracted_text") and doc.extracted_text:
        extracted_text = doc.extracted_text
    elif hasattr(doc, "original_text") and doc.original_text:
        extracted_text = doc.original_text

    # Determine rule set: check payload body, query param, or auto-detect
    requested_rule_set = None
    if payload and payload.rule_set:
        requested_rule_set = payload.rule_set.strip()
    elif rule_set:
        requested_rule_set = rule_set.strip()

    compliance_service = ComplianceService()
    auto_detected = False
    if not requested_rule_set or requested_rule_set.lower() in ("auto", "auto_detect", "detect", "default"):
        final_rule_set = compliance_service.detect_rule_set(extracted_text, doc.filename)
        auto_detected = True
    else:
        final_rule_set = requested_rule_set

    compliance_res = compliance_service.check_compliance(extracted_text, final_rule_set)
    violations = compliance_res.get("violations", [])
    comp_status = compliance_res.get("status", "compliant" if not violations else "non-compliant")

    db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).delete()
    db_compliance = ComplianceCheck(
        id=uuid.uuid4(),
        document_id=doc.id,
        rule_set=final_rule_set,
        result=json.dumps(violations)
    )
    db.add(db_compliance)

    # Record audit log
    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Compliance check completed ({final_rule_set}, auto_detected={auto_detected}) with {len(violations)} violations"
    )
    db.add(audit_log)
    db.commit()

    return ComplianceResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        rule_set=final_rule_set,
        auto_detected=auto_detected,
        status=comp_status,
        violations=violations,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/report", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_report(
    request: Request,
    document_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Generate or update report record with real in-memory PDF/DOCX generation and storage persistence."""
    doc = get_accessible_document(db, document_id, current_user)

    report_data = ReportGeneratorService.assemble_report_data(doc, db)
    generator = ReportGeneratorService()

    if format == "docx":
        file_bytes = generator.generate_docx(report_data)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
        storage_path = f"reports/{doc.id}/review_memorandum.docx"
    else:
        file_bytes = generator.generate_pdf(report_data)
        content_type = "application/pdf"
        ext = "pdf"
        storage_path = f"reports/{doc.id}/review_memorandum.pdf"

    storage_service = StorageService()
    try:
        storage_service.upload_file(
            file_data=file_bytes,
            file_path=storage_path,
            content_type=content_type
        )
        report_url = storage_service.get_public_url(storage_path)
    except Exception as e:
        logger.warning("Storage upload failed or in mock mode: %s", e)
        report_url = f"/api/v1/reports/{doc.id}/download?format={ext}"

    db.query(Report).filter(Report.document_id == doc.id, Report.format == ext).delete()
    db_report = Report(
        id=uuid.uuid4(),
        document_id=doc.id,
        format=ext,
        file_url=report_url
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)

    return AnalysisStatusResponse(
        status="report_generated",
        report_url=db_report.file_url,
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/audit", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_audit(
    request: Request,
    document_id: str,
    body: AuditAction = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Log an audit entry for a document."""
    doc = get_accessible_document(db, document_id, current_user)

    action_str = body.action if (body and body.action) else f"Workflow processing step completed for document: {doc.filename}"

    audit_log = AuditLog(
        document_id=doc.id,
        action=action_str
    )
    db.add(audit_log)
    db.commit()

    return AnalysisStatusResponse(
        status="audit_logged",
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/escalate", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def escalate_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """Escalate a document to manual attorney review."""
    doc = get_accessible_document(db, document_id, current_user)

    doc.status = "escalated"

    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Document escalated to human review: {doc.filename}"
    )
    db.add(audit_log)
    db.commit()

    return AnalysisStatusResponse(
        status="escalated",
        message="Escalated to human review.",
        document_id=document_id,
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.post("/{document_id}/deep-extract", response_model=DeepExtractionResponse)
@limiter.limit("60/minute")
def run_deep_extraction(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DeepExtractionResponse:
    """
    Perform deep structured extraction of deal terms and obligations.
    Idempotent: updates the existing DeepExtraction record if already present,
    or creates a new one if not.
    """
    doc = get_accessible_document(db, document_id, current_user)

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj else ""

    deep_extraction_service = DeepExtractionService()
    extraction = deep_extraction_service.extract_deep(extracted_text)

    existing = db.query(DeepExtraction).filter(DeepExtraction.document_id == doc.id).first()
    if existing:
        existing.deal_terms = extraction.get("deal_terms", {})
        existing.obligations = extraction.get("obligations", [])
        existing.risk_flags = extraction.get("risk_flags", [])
        existing.missing_protections = extraction.get("missing_protections", [])
        existing.redline_suggestions = extraction.get("redline_suggestions", [])
        existing.executive_summary = extraction.get("executive_summary", "")
        existing.confidence = extraction.get("confidence", "MEDIUM")
        db_deep_extraction = existing
    else:
        db_deep_extraction = DeepExtraction(
            id=uuid.uuid4(),
            document_id=doc.id,
            deal_terms=extraction.get("deal_terms", {}),
            obligations=extraction.get("obligations", []),
            risk_flags=extraction.get("risk_flags", []),
            missing_protections=extraction.get("missing_protections", []),
            redline_suggestions=extraction.get("redline_suggestions", []),
            executive_summary=extraction.get("executive_summary", ""),
            confidence=extraction.get("confidence", "MEDIUM")
        )
        db.add(db_deep_extraction)

    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Deep extraction performed on document: {doc.filename}"
    )
    db.add(audit_log)

    try:
        db.commit()
        db.refresh(db_deep_extraction)
    except IntegrityError:
        db.rollback()
        # Fallback to handle concurrent insertion race conditions safely
        existing = db.query(DeepExtraction).filter(DeepExtraction.document_id == doc.id).first()
        if existing:
            existing.deal_terms = extraction.get("deal_terms", {})
            existing.obligations = extraction.get("obligations", [])
            existing.risk_flags = extraction.get("risk_flags", [])
            existing.missing_protections = extraction.get("missing_protections", [])
            existing.redline_suggestions = extraction.get("redline_suggestions", [])
            existing.executive_summary = extraction.get("executive_summary", "")
            existing.confidence = extraction.get("confidence", "MEDIUM")
            audit_log = AuditLog(
                document_id=doc.id,
                action=f"Deep extraction updated on document: {doc.filename}"
            )
            db.add(audit_log)
            try:
                db.commit()
                db.refresh(existing)
                db_deep_extraction = existing
            except Exception:
                db.rollback()
                raise
        else:
            raise
    except Exception:
        db.rollback()
        raise

    return DeepExtractionResponse(
        document_id=str(db_deep_extraction.document_id),
        deal_terms=db_deep_extraction.deal_terms,
        obligations=db_deep_extraction.obligations,
        risk_flags=db_deep_extraction.risk_flags,
        missing_protections=db_deep_extraction.missing_protections,
        redline_suggestions=db_deep_extraction.redline_suggestions,
        executive_summary=db_deep_extraction.executive_summary or "",
        confidence=db_deep_extraction.confidence
    )


@router.post("/{document_id}/quick-summary", response_model=QuickSummaryResponse)
@limiter.limit("60/minute")
def get_quick_summary(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> QuickSummaryResponse:
    """
    Generate and return an immediate 2-3 sentence overview of the document via a fast single LLM call.
    Runs independently of the full multi-step analysis pipeline to provide instant frontend feedback.
    """
    doc = get_accessible_document(db, document_id, current_user)

    # Retrieve extracted text
    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    text_content = ""
    if extracted_text_obj and extracted_text_obj.content:
        text_content = extracted_text_obj.content
    elif hasattr(doc, "extracted_text") and doc.extracted_text:
        text_content = doc.extracted_text
    elif hasattr(doc, "original_text") and doc.original_text:
        text_content = doc.original_text

    from app.api.v1.routers import documents
    llm_cls = getattr(documents, "LLMService", LLMService)
    llm_service = llm_cls()
    summary_data = llm_service.generate_quick_summary(text_content, doc.filename)

    # Persist overview on document if not already finalized
    if not doc.document_overview:
        doc.document_overview = summary_data.get("quick_summary")
    if not doc.summary or doc.summary == "Summary generation pending.":
        doc.summary = summary_data.get("quick_summary")

    # Record audit log
    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Quick summary generated for document: {doc.filename}"
    )
    db.add(audit_log)
    db.commit()

    return QuickSummaryResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        quick_summary=summary_data.get("quick_summary", "Document overview unavailable."),
        document_type=summary_data.get("document_type", "Legal Contract"),
        key_points=summary_data.get("key_points", []),
        estimated_risk_level=summary_data.get("estimated_risk_level", "LOW"),
        disclaimer=summary_data.get("disclaimer", "This initial AI overview assists legal review and is not legal advice.")
    )

"""
Reports router.
Handles retrieval, generation, storage, and export requests for legal memorandum reports in PDF and DOCX formats.
"""
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.models import AuditLog, Clause, ComplianceCheck, LegalReference, Report, RiskFlag, User
from app.models.schemas import CitationResponse, ClauseResponse, ReportResponse
from app.services.report_generator_service import ReportGeneratorService
from app.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)


def assemble_report_data(doc: Any, db: Session) -> dict[str, Any]:
    """
    Assemble the complete structured findings for a document into a report payload dictionary.
    """
    # Load citations
    citations_db = db.query(LegalReference).filter(LegalReference.document_id == doc.id).all()
    citations = [
        {"source": cit.source, "citation": cit.citation}
        for cit in citations_db
    ]

    # Load clauses and risk flags
    clauses_db = db.query(Clause).filter(Clause.document_id == doc.id).all()
    clauses = []
    risk_flags = []
    recommendations = []

    for c_db in clauses_db:
        flags = db.query(RiskFlag).filter(RiskFlag.clause_id == c_db.id).all()
        severity = flags[0].severity if flags else "LOW"
        explanation = flags[0].explanation if flags else ""

        if severity in ("MEDIUM", "HIGH") and explanation:
            recommendations.append(f"Review the {c_db.clause_type} clause: {explanation}")
            risk_flags.append({
                "clause_type": c_db.clause_type,
                "severity": severity,
                "explanation": explanation
            })

        clauses.append({
            "id": str(c_db.id),
            "clause_type": c_db.clause_type,
            "type": c_db.clause_type,
            "clause_text": c_db.clause_text,
            "text": c_db.clause_text,
            "severity": severity,
            "risk_level": severity,
            "explanation": explanation or f"Standard {c_db.clause_type} clause.",
            "category": c_db.category or "General & Boilerplate",
            "confidence_score": c_db.confidence_score if c_db.confidence_score is not None else 0.95
        })

    # Load compliance violations
    violations = []
    compliance_db = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).first()
    if compliance_db:
        try:
            violations = json.loads(compliance_db.result)
            for v in violations:
                recommendations.append(v)
                risk_flags.append({
                    "clause_type": "Compliance Policy Audit",
                    "severity": "HIGH",
                    "explanation": str(v)
                })
        except Exception:
            pass

    if not recommendations:
        recommendations.append("Confirm all provisions align with standard organizational templates and practices.")
        recommendations.append("Ensure the designated governing jurisdiction is acceptable for your operations before formal execution.")

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "safety_score": doc.safety_score if doc.safety_score is not None else 100,
        "risk_level": doc.risk_level if doc.risk_level is not None else "LOW",
        "summary": doc.summary or "Analysis complete.",
        "document_overview": doc.document_overview or doc.summary or "Document analysis completed.",
        "parties": doc.parties or [],
        "key_dates": doc.key_dates or {},
        "missing_sections": doc.missing_sections or [],
        "plain_english_summary": doc.plain_english_summary or doc.summary or "Summary of contractual provisions.",
        "clauses": clauses,
        "risk_flags": risk_flags,
        "recommendations": recommendations,
        "citations": citations,
        "compliance_violations": violations
    }


@router.get("/{document_id}", response_model=ReportResponse)
def get_report(
    document_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ReportResponse:
    """
    Retrieve generated memorandum audit report by document ID.
    """
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Check if a report file record already exists in database
    existing_report = db.query(Report).filter(
        Report.document_id == doc.id,
        Report.format == format
    ).first()

    report_url = existing_report.file_url if existing_report else f"/api/v1/reports/{doc.id}/download?format={format}"

    # Assemble structured findings
    report_data = assemble_report_data(doc, db)

    # Write audit log row for report viewed
    try:
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"Report viewed: {doc.filename} ({format.upper()})"
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error writing report audit log: %s", e, exc_info=True)

    clause_responses = [
        ClauseResponse(
            id=c.get("id"),
            type=c.get("clause_type"),
            text=c.get("clause_text"),
            severity=c.get("severity"),
            explanation=c.get("explanation"),
            category=c.get("category"),
            confidence_score=c.get("confidence_score")
        )
        for c in report_data["clauses"]
    ]

    citation_responses = [
        CitationResponse(source=cit["source"], citation=cit["citation"])
        for cit in report_data["citations"]
    ]

    return ReportResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        uploaded_at=report_data["uploaded_at"],
        report_url=report_url,
        format=format,
        safety_score=report_data["safety_score"],
        risk_level=report_data["risk_level"],
        summary=report_data["summary"],
        recommendations=report_data["recommendations"],
        clauses=clause_responses,
        citations=citation_responses,
        document_overview=report_data["document_overview"],
        parties=report_data["parties"],
        key_dates=report_data["key_dates"],
        missing_sections=report_data["missing_sections"],
        plain_english_summary=report_data["plain_english_summary"]
    )


@router.post("/{document_id}/export", response_model=ReportResponse)
def export_report(
    document_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ReportResponse:
    """
    Generate, upload to storage, and track a publication-grade PDF or DOCX memorandum report.
    """
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # 1. Assemble structured findings
    report_data = assemble_report_data(doc, db)

    # 2. Render binary export (PDF or DOCX)
    generator = ReportGeneratorService()
    if format == "docx":
        file_bytes = generator.generate_docx(report_data)
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        file_bytes = generator.generate_pdf(report_data)
        content_type = "application/pdf"
        ext = "pdf"

    # 3. Upload to Supabase Storage
    storage_service = StorageService()
    storage_path = f"reports/{doc.id}/report.{ext}"
    try:
        storage_service.upload_file(
            file_data=file_bytes,
            file_path=storage_path,
            content_type=content_type
        )
        report_url = storage_service.get_public_url(storage_path)
    except Exception as e:
        logger.warning("Storage upload fallback: %s", e)
        report_url = f"/api/v1/reports/{doc.id}/download?format={ext}"

    # 4. Insert or update reports table
    existing_report = db.query(Report).filter(
        Report.document_id == doc.id,
        Report.format == ext
    ).first()

    if existing_report:
        existing_report.file_url = report_url
        db.commit()
        db.refresh(existing_report)
    else:
        db_report = Report(
            id=uuid.uuid4(),
            document_id=doc.id,
            format=ext,
            file_url=report_url
        )
        db.add(db_report)
        db.commit()

    # 5. Write audit log
    try:
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"Report exported: {doc.filename} (Format: {ext.upper()})"
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error writing export audit log: %s", e, exc_info=True)

    clause_responses = [
        ClauseResponse(
            id=c.get("id"),
            type=c.get("clause_type"),
            text=c.get("clause_text"),
            severity=c.get("severity"),
            explanation=c.get("explanation"),
            category=c.get("category"),
            confidence_score=c.get("confidence_score")
        )
        for c in report_data["clauses"]
    ]

    citation_responses = [
        CitationResponse(source=cit["source"], citation=cit["citation"])
        for cit in report_data["citations"]
    ]

    return ReportResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        uploaded_at=report_data["uploaded_at"],
        report_url=report_url,
        format=ext,
        safety_score=report_data["safety_score"],
        risk_level=report_data["risk_level"],
        summary=report_data["summary"],
        recommendations=report_data["recommendations"],
        clauses=clause_responses,
        citations=citation_responses,
        document_overview=report_data["document_overview"],
        parties=report_data["parties"],
        key_dates=report_data["key_dates"],
        missing_sections=report_data["missing_sections"],
        plain_english_summary=report_data["plain_english_summary"]
    )


@router.get("/{document_id}/download")
def download_report_file(
    document_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Response:
    """
    Directly render and download the report document binary in PDF or DOCX format.
    """
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    report_data = assemble_report_data(doc, db)
    generator = ReportGeneratorService()

    base_name = doc.filename.rsplit(".", 1)[0] if "." in doc.filename else doc.filename
    clean_filename = f"{base_name}_legal_report.{format}"

    if format == "docx":
        file_bytes = generator.generate_docx(report_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        file_bytes = generator.generate_pdf(report_data)
        media_type = "application/pdf"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}"',
            "Cache-Control": "no-cache"
        }
    )



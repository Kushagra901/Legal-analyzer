"""
Reports router.
Handles retrieval, generation, storage, and export requests for legal memorandum reports in PDF and DOCX formats.
"""
import io
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.models import AuditLog, Report, User
from app.models.schemas import CitationResponse, ClauseResponse, ReportResponse
from app.services.report_generator_service import ReportGeneratorService
from app.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)


def assemble_report_data(doc: Any, db: Session) -> dict[str, Any]:
    """
    Assemble the complete structured findings for a document into a report payload dictionary.
    """
    return ReportGeneratorService.assemble_report_data(doc, db)



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
    storage_path = f"reports/{doc.id}/review_memorandum.{ext}"
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
) -> StreamingResponse:
    """
    Directly render and stream the report document binary in PDF or DOCX format.
    """
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    report_data = assemble_report_data(doc, db)
    generator = ReportGeneratorService()

    if format == "docx":
        file_bytes = generator.generate_docx(report_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"Legal_Review_{document_id}.docx"
    else:
        file_bytes = generator.generate_pdf(report_data)
        media_type = "application/pdf"
        filename = f"Legal_Review_{document_id}.pdf"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )



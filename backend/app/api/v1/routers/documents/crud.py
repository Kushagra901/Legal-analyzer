"""
CRUD router for documents.
Handles document upload, retrieval, listing, status checking, and deletion.
"""

import json
import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import (
    AuditLog,
    AutomationRun,
    Clause,
    ClauseReview,
    ComplianceCheck,
    Document,
    ExtractedText,
    LegalReference,
    Report,
    RiskFlag,
    User,
)
from app.models.schemas import (
    AnalysisDetailResponse,
    AnalysisStatusResponse,
    CitationResponse,
    ClauseResponse,
    DocumentListItemResponse,
    DocumentResponse,
    UploadResponse,
)
from app.services.ocr_service import OCRService
from app.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/rtf",
    "text/rtf",
    "text/html",
    "image/jpeg",
    "image/png",
    "image/tiff",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_test_user_exists(db: Session) -> uuid.UUID:
    """
    Ensures a test organization, auth user, and public user profile exist.
    Returns the test user UUID.
    """
    test_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    if db.bind.dialect.name == "sqlite":
        try:
            db.execute(text("""
                INSERT INTO organizations (id, name, plan)
                VALUES (:id, 'Test Org', 'free')
                ON CONFLICT (id) DO NOTHING;
            """), {"id": str(test_id)})
            db.execute(text("""
                INSERT INTO users (id, org_id, email, role)
                VALUES (:id, :id, 'test@example.com', 'user')
                ON CONFLICT (id) DO NOTHING;
            """), {"id": str(test_id)})
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("SQLite ensure_test_user_exists warning: %s", e)
        return test_id

    # For PostgreSQL (Supabase)
    try:
        # 1. Create Organization
        db.execute(text("""
            INSERT INTO public.organizations (id, name, plan)
            VALUES (:id, 'Test Org', 'free')
            ON CONFLICT (id) DO NOTHING;
        """), {"id": test_id})

        # 2. Create Auth User
        db.execute(text("""
            INSERT INTO auth.users (id, email, aud, role)
            VALUES (:id, 'test@example.com', 'authenticated', 'authenticated')
            ON CONFLICT (id) DO NOTHING;
        """), {"id": test_id})

        # 3. Create Public User Profile
        db.execute(text("""
            INSERT INTO public.users (id, org_id, email, role)
            VALUES (:id, :id, 'test@example.com', 'user')
            ON CONFLICT (id) DO NOTHING;
        """), {"id": test_id})

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("ensure_test_user_exists failed: %s", e)

    return test_id


async def trigger_n8n_webhook(document_id: str, filename: str, email: str = "") -> None:
    """
    Triggers n8n production webhook after successful document upload.
    Sends POST with document_id, filename, and user email.
    """
    import httpx

    from app.core.config import settings
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "document_id": document_id,
                "filename": filename,
                "email": email
            }
            headers = {
                "X-Webhook-Secret": settings.INTERNAL_SERVICE_TOKEN,
                "Content-Type": "application/json"
            }
            response = await client.post(
                settings.N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            logger.info("Successfully triggered n8n webhook for document %s (email: %s)", document_id, email)
    except Exception as e:
        logger.warning("Failed to trigger n8n webhook for document %s: %s", document_id, e)


@router.post("/", response_model=UploadResponse)
@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UploadResponse:
    """
    Upload a document, validate it, save it to storage, and return processing status.
    Wraps entire pipeline (validation, storage, OCR) in try/except to prevent connection reset.
    """
    try:
        filename = file.filename or "uploaded_document"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        allowed_exts = {"pdf", "txt", "docx", "doc", "rtf", "html", "htm", "jpg", "jpeg", "png", "tiff", "tif"}

        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '.{ext}'. Supported formats: {', '.join(sorted(allowed_exts))}."
            )

        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{file.content_type}' is not permitted."
            )

        # 2. Validate file size
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum limit of 10MB."
            )

        # Magic-byte signature validation
        MAGIC_SIGNATURES = {
            "pdf": [b"%PDF"],
            "docx": [b"PK\x03\x04"],
            "png": [b"\x89PNG\r\n\x1a\n"],
            "jpg": [b"\xff\xd8\xff"],
            "jpeg": [b"\xff\xd8\xff"],
        }
        expected_magics = MAGIC_SIGNATURES.get(ext)
        if expected_magics and not any(content.startswith(magic) for magic in expected_magics):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match the expected signature for a .{ext} document."
            )

        # 3. Upload to Supabase Storage
        storage_service = StorageService()
        unique_filename = f"{uuid.uuid4()}/{filename}"
        try:
            storage_path = storage_service.upload_file(
                file_data=content,
                file_path=unique_filename,
                content_type=file.content_type or "application/octet-stream"
            )
        except Exception as storage_err:
            logger.warning("Storage Service error (continuing with mock path): %s", storage_err)
            storage_path = f"documents/{unique_filename}"

        # 4. Extract Text Natively or via Tesseract OCR Fallback
        ocr_service = OCRService()
        extracted_text, method, parsing_confidence = ocr_service.process_document(content)

        # 5. Save to Database
        db_doc = Document(
            filename=filename,
            user_id=current_user.id,
            status="processing"
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)

        # 6. Save Extracted Text in public.extracted_text table
        try:
            db_extracted = ExtractedText(
                id=uuid.uuid4(),
                document_id=db_doc.id,
                content=extracted_text,
                method=method,
                parsing_confidence=parsing_confidence
            )
            db.add(db_extracted)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Error saving extracted text to database: %s", e, exc_info=True)

        # 7. Write initial audit log
        try:
            audit_log = AuditLog(
                document_id=db_doc.id,
                action=f"Document uploaded and queued for processing: {filename} (Size: {file_size} bytes, Status: {db_doc.status})"
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Error saving upload audit log: %s", e, exc_info=True)

        # 8. Trigger Celery Asynchronous Task or background execution
        doc_id_str = str(db_doc.id)
        celery_dispatched = False
        import socket
        try:
            # Fast check if Redis port is listening to prevent kombu retry timeouts
            sock = socket.create_connection(("localhost", 6379), timeout=0.1)
            sock.close()
            from app.workers.tasks import analyze_document_task
            analyze_document_task.delay(doc_id_str)
            celery_dispatched = True
        except Exception as celery_err:
            logger.warning("Celery/Redis unavailable (%s), falling back to FastAPI background execution.", celery_err)

        if not celery_dispatched:
            from app.workers.tasks import execute_document_analysis
            background_tasks.add_task(execute_document_analysis, doc_id_str)

        # 9. Trigger n8n webhook in background
        user_email = current_user.email or ""
        from app.api.v1.routers import documents
        webhook_caller = getattr(documents, "trigger_n8n_webhook", trigger_n8n_webhook)
        background_tasks.add_task(webhook_caller, doc_id_str, db_doc.filename, user_email)

        return UploadResponse(
            document_id=doc_id_str,
            filename=db_doc.filename,
            status=db_doc.status,
            uploaded_at=db_doc.uploaded_at.isoformat(),
            storage_path=storage_path
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.error("Unhandled exception during document upload", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing document upload. Please try again or contact support."
        )


@router.get("/", response_model=list[DocumentListItemResponse])
@limiter.limit("60/minute")
def list_documents(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[DocumentListItemResponse]:
    """
    Retrieve all uploaded documents.
    """
    if current_user.role == "admin":
        docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    else:
        docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentListItemResponse(
            document_id=str(doc.id),
            filename=doc.filename,
            status=doc.status,
            uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else None
        )
        for doc in docs
    ]


@router.get("/{document_id}/status", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def get_document_status(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """
    Retrieve document processing status, progress percentage, and error details.
    """
    doc = get_accessible_document(db, document_id, current_user)

    progress_map = {
        "uploaded": 25,
        "processing": 50,
        "flagged": 75,
        "completed": 100,
        "failed": 0
    }
    progress_val = progress_map.get(doc.status, 50)
    error_msg = doc.summary if doc.status == "failed" else None

    return AnalysisStatusResponse(
        status=doc.status,
        progress=progress_val,
        error=error_msg,
        document_id=str(doc.id),
        filename=doc.filename,
        safety_score=doc.safety_score,
        risk_level=doc.risk_level
    )


@router.get("/{document_id}", response_model=DocumentResponse)
@limiter.limit("60/minute")
def get_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """
    Retrieve details for an analyzed document.
    """
    doc = get_accessible_document(db, document_id, current_user)

    # Write audit log
    try:
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"Document viewed: {doc.filename}"
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error writing view audit log: %s", e, exc_info=True)

    # Load real extracted text from database
    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    original_text = extracted_text_obj.content if extracted_text_obj else ""

    # Load Clauses
    clauses_db = db.query(Clause).filter(Clause.document_id == doc.id).all()
    clauses = []
    recommendations = []

    for c_db in clauses_db:
        # Load risk flags linked to this clause
        flags = db.query(RiskFlag).filter(RiskFlag.clause_id == c_db.id).all()
        severity = "LOW"
        explanation = ""
        if flags:
            severity = flags[0].severity
            explanation = flags[0].explanation
            if severity in ("MEDIUM", "HIGH"):
                recommendations.append(f"Review the {c_db.clause_type} clause: {explanation}")

        clauses.append(ClauseResponse(
            id=str(c_db.id),
            type=c_db.clause_type,
            text=c_db.clause_text,
            explanation=explanation or f"Standard {c_db.clause_type} clause.",
            severity=severity
        ))

    # Load citations
    citations_db = db.query(LegalReference).filter(LegalReference.document_id == doc.id).all()
    citations = [
        CitationResponse(
            source=cit.source,
            citation=cit.citation
        )
        for cit in citations_db
    ]

    # Load compliance violations
    violations = []
    compliance_db = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).first()
    if compliance_db:
        try:
            violations = json.loads(compliance_db.result)
        except Exception:
            violations = []

    for v in violations:
        recommendations.append(v)

    if not recommendations:
        recommendations.append("Confirm all provisions align with standard organizational templates and practices.")
        recommendations.append("Ensure the designated governing jurisdiction is acceptable for your operations before formal execution.")

    return DocumentResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        status=doc.status,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        original_text=original_text,
        analysis=AnalysisDetailResponse(
            safety_score=doc.safety_score if doc.safety_score is not None else 100,
            risk_level=doc.risk_level if doc.risk_level is not None else "LOW",
            summary=doc.summary or "Analysis complete.",
            clauses=clauses,
            citations=citations,
            recommendations=recommendations,
            compliance_violations=violations
        )
    )


@router.delete("/{document_id}", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def delete_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    """
    Delete a document and all related analysis, extracted text, and audit logs.
    Enforces ownership verification: non-admin users cannot delete other users' documents.
    """
    doc = get_accessible_document(db, document_id, current_user)
    filename = doc.filename
    doc_id = doc.id

    try:
        # 1. Clean up child records referencing clauses first (ClauseReview, RiskFlag)
        clause_ids = [c[0] for c in db.query(Clause.id).filter(Clause.document_id == doc_id).all()]
        if clause_ids:
            db.query(ClauseReview).filter(ClauseReview.clause_id.in_(clause_ids)).delete(synchronize_session=False)
            db.query(RiskFlag).filter(RiskFlag.clause_id.in_(clause_ids)).delete(synchronize_session=False)
        else:
            db.query(ClauseReview).filter(ClauseReview.document_id == doc_id).delete(synchronize_session=False)

        # 2. Clean up clauses
        db.query(Clause).filter(Clause.document_id == doc_id).delete(synchronize_session=False)

        # 3. Clean up other records referencing document_id
        db.query(ExtractedText).filter(ExtractedText.document_id == doc_id).delete(synchronize_session=False)
        db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc_id).delete(synchronize_session=False)
        db.query(LegalReference).filter(LegalReference.document_id == doc_id).delete(synchronize_session=False)
        db.query(Report).filter(Report.document_id == doc_id).delete(synchronize_session=False)
        db.query(AutomationRun).filter(AutomationRun.document_id == doc_id).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.document_id == doc_id).delete(synchronize_session=False)

        # 4. Delete the document record itself
        db.delete(doc)

        # 5. Record deletion audit log
        delete_log = AuditLog(
            document_id=None,
            action=f"Document deleted: {filename} (ID: {document_id})"
        )
        db.add(delete_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Error deleting document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete document deletion."
        )

    return AnalysisStatusResponse(
        status="deleted",
        message="Document successfully deleted.",
        document_id=document_id,
        filename=filename
    )

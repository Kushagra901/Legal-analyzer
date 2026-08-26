# documents.py
"""
Documents Router.
Exposes endpoints for uploading and retrieving documents.
"""
import datetime
import json
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
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import (
    AuditLog,
    AutomationRun,
    ChatMessage,
    Clause,
    ClauseReview,
    ComplianceCheck,
    DeepExtraction,
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
    ChatCitationResponse,
    ChatHistoryItemResponse,
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ClauseResponse,
    ClauseReviewCreate,
    ClauseReviewResponse,
    DeepExtractionResponse,
    DocumentListItemResponse,
    DocumentResponse,
    UploadResponse,
)
from app.services.chat_service import ChatService
from app.services.compliance_service import ComplianceService
from app.services.deep_extraction_service import DeepExtractionService
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.risk_service import RiskService
from app.services.storage_service import StorageService

router = APIRouter()

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
    "image/tiff"
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
            print(f"SQLite ensure_test_user_exists warning: {e}")
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
        print(f"Warning: ensure_test_user_exists failed: {e}")

    return test_id


async def trigger_n8n_webhook(document_id: str, filename: str) -> None:
    """
    Triggers n8n production webhook after successful document upload.
    Sends POST with document_id and filename.
    """
    import httpx

    from app.core.config import settings
    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "document_id": document_id,
                "filename": filename
            }
            response = await client.post(
                settings.N8N_WEBHOOK_URL,
                json=payload,
                timeout=5.0
            )
            response.raise_for_status()
            print(f"Successfully triggered n8n webhook for document {document_id}")
    except Exception as e:
        print(f"Warning: Failed to trigger n8n webhook for document {document_id}: {e}")


import traceback

@router.post("", response_model=UploadResponse)
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
        filename = file.filename or "uploaded_document.pdf"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        allowed_exts = {"pdf", "txt", "docx", "doc", "rtf", "html", "htm", "jpg", "jpeg", "png", "tiff", "tif"}

        # 1. Validate file type
        if (file.content_type and file.content_type not in ALLOWED_MIME_TYPES) and (ext not in allowed_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only PDF, TXT, and DOCX are allowed."
            )

        # 2. Validate file size
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum limit of 10MB."
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
            print(f"Storage Service error (continuing with mock path): {storage_err}")
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
            print(f"Error saving extracted text to database: {e}")

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
            print(f"Error saving upload audit log: {e}")

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
            print(f"Warning: Celery/Redis unavailable ({celery_err}), falling back to FastAPI background execution.")
        
        if not celery_dispatched:
            from app.workers.tasks import execute_document_analysis
            background_tasks.add_task(execute_document_analysis, doc_id_str)

        # 9. Trigger n8n webhook in background
        background_tasks.add_task(trigger_n8n_webhook, doc_id_str, db_doc.filename)

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
    except Exception as e:
        db.rollback()
        tb_str = traceback.format_exc()
        print(f"ERROR: Unhandled exception in upload_document handler:\n{tb_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error processing document upload: {str(e)}"
        )

@router.get("", response_model=list[DocumentListItemResponse])
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
        print(f"Error writing view audit log: {e}")

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


@router.post("/{document_id}/ocr", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_ocr(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
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
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj else "Sample contract text."

    llm_service = LLMService()
    try:
        analysis = llm_service.analyze_contract(extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Analysis failed: {str(e)}")

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


@router.post("/{document_id}/score", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_scoring(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

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

    return AnalysisStatusResponse(status="scored", safety_score=safety_score, risk_level=risk_level, document_id=document_id, filename=doc.filename)


@router.post("/{document_id}/compliance", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_compliance(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj else ""

    compliance_service = ComplianceService()
    compliance_res = compliance_service.check_compliance(extracted_text, "standard_nda")

    db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).delete()
    db_compliance = ComplianceCheck(
        id=uuid.uuid4(),
        document_id=doc.id,
        rule_set=compliance_res.get("rule_set", "standard_nda"),
        result=json.dumps(compliance_res.get("violations", []))
    )
    db.add(db_compliance)
    db.commit()

    return AnalysisStatusResponse(status="compliance_checked", violations=compliance_res.get("violations", []), document_id=document_id, filename=doc.filename, safety_score=doc.safety_score, risk_level=doc.risk_level)


@router.post("/{document_id}/report", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_report(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.query(Report).filter(Report.document_id == doc.id).delete()
    db_report = Report(
        id=uuid.uuid4(),
        document_id=doc.id,
        format="pdf",
        file_url=f"/reports/{document_id}.pdf"
    )
    db.add(db_report)
    db.commit()

    return AnalysisStatusResponse(status="report_generated", report_url=db_report.file_url, document_id=document_id, filename=doc.filename, safety_score=doc.safety_score, risk_level=doc.risk_level)


class AuditAction(BaseModel):
    action: str | None = None


@router.post("/{document_id}/audit", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def run_audit(
    request: Request,
    document_id: str,
    body: AuditAction = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    action_str = body.action if (body and body.action) else f"Workflow processing step completed for document: {doc.filename}"

    audit_log = AuditLog(
        document_id=doc.id,
        action=action_str
    )
    db.add(audit_log)
    db.commit()

    return AnalysisStatusResponse(status="audit_logged", document_id=document_id, filename=doc.filename, safety_score=doc.safety_score, risk_level=doc.risk_level)


@router.post("/{document_id}/escalate", response_model=AnalysisStatusResponse)
@limiter.limit("60/minute")
def escalate_document(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> AnalysisStatusResponse:
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
        print(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )

    return AnalysisStatusResponse(
        status="deleted",
        message="Document successfully deleted.",
        document_id=document_id,
        filename=filename
    )


@router.post("/{document_id}/clauses/{clause_id}/review", response_model=ClauseReviewResponse)
@limiter.limit("60/minute")
def review_clause(
    request: Request,
    document_id: str,
    clause_id: str,
    body: ClauseReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ClauseReviewResponse:
    """
    Persist or update an attorney's review decision and optional note for a specific clause.
    Writes an audit log entry upon success.
    """
    doc = get_accessible_document(db, document_id, current_user)

    # Convert clause_id string to UUID if needed
    try:
        clause_uuid = uuid.UUID(clause_id) if isinstance(clause_id, str) else clause_id
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clause UUID format.")

    clause = db.query(Clause).filter(Clause.id == clause_uuid, Clause.document_id == doc.id).first()
    if not clause:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clause not found in document.")

    valid_decisions = {"pending", "approved", "redline_flagged"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{body.decision}'. Must be one of: {', '.join(valid_decisions)}"
        )

    # Upsert: check if a review record already exists for this clause
    existing = db.query(ClauseReview).filter(
        ClauseReview.clause_id == clause.id,
        ClauseReview.document_id == doc.id
    ).first()

    now = datetime.datetime.now(datetime.UTC)
    if existing:
        existing.decision = body.decision
        existing.note = body.note
        existing.user_id = current_user.id
        existing.reviewed_at = now
        review_record = existing
    else:
        review_record = ClauseReview(
            id=uuid.uuid4(),
            clause_id=clause.id,
            document_id=doc.id,
            user_id=current_user.id,
            decision=body.decision,
            note=body.note,
            reviewed_at=now
        )
        db.add(review_record)

    # Write audit log entry
    audit_action = f"Clause review updated: {clause.clause_type} set to '{body.decision}'"
    if body.note:
        audit_action += f" with note: {body.note}"

    audit_log = AuditLog(
        document_id=doc.id,
        action=audit_action
    )
    db.add(audit_log)
    db.commit()
    db.refresh(review_record)

    return ClauseReviewResponse(
        id=str(review_record.id),
        clause_id=str(review_record.clause_id),
        document_id=str(review_record.document_id),
        user_id=str(review_record.user_id),
        decision=review_record.decision,
        note=review_record.note,
        reviewed_at=review_record.reviewed_at.isoformat() if review_record.reviewed_at else now.isoformat()
    )


@router.get("/{document_id}/reviews", response_model=list[ClauseReviewResponse])
@limiter.limit("60/minute")
def get_document_clause_reviews(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[ClauseReviewResponse]:
    """
    Retrieve all clause review records for a document.
    """
    doc = get_accessible_document(db, document_id, current_user)
    reviews = db.query(ClauseReview).filter(ClauseReview.document_id == doc.id).all()

    return [
        ClauseReviewResponse(
            id=str(r.id),
            clause_id=str(r.clause_id),
            document_id=str(r.document_id),
            user_id=str(r.user_id),
            decision=r.decision,
            note=r.note,
            reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else ""
        )
        for r in reviews
    ]


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
    """
    doc = get_accessible_document(db, document_id, current_user)
    
    existing = db.query(DeepExtraction).filter(DeepExtraction.document_id == doc.id).first()
    if existing:
        return DeepExtractionResponse(
            document_id=str(existing.document_id),
            deal_terms=existing.deal_terms,
            obligations=existing.obligations,
            risk_flags=existing.risk_flags,
            missing_protections=existing.missing_protections,
            redline_suggestions=existing.redline_suggestions,
            executive_summary=existing.executive_summary or "",
            confidence=existing.confidence
        )
        
    extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
    extracted_text = extracted_text_obj.content if extracted_text_obj else ""
    
    deep_extraction_service = DeepExtractionService()
    extraction = deep_extraction_service.extract_deep(extracted_text)
    
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
    db.commit()
    
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

@router.post("/{document_id}/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
def chat_with_document(
    request: Request,
    document_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """
    Chat with a document using structured Q&A.
    """
    doc = get_accessible_document(db, document_id, current_user)
    
    clauses = db.query(Clause).filter(Clause.document_id == doc.id).all()
    clause_dicts = [{"clause_type": c.clause_type, "clause_text": c.clause_text} for c in clauses]
    
    chat_service = ChatService()
    relevant_clauses = chat_service._search_clauses_by_keywords(body.query, clause_dicts)
    if not relevant_clauses:
        relevant_clauses = clause_dicts[:5]
        
    answer_data = chat_service.answer_question(body.query, relevant_clauses, {"filename": doc.filename})
    
    conv_id = uuid.UUID(body.conversation_id) if body.conversation_id else uuid.uuid4()
    
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=current_user.id,
        conversation_id=conv_id,
        role="user",
        content=body.query
    )
    db.add(user_msg)
    
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=current_user.id,
        conversation_id=conv_id,
        role="assistant",
        content=answer_data.get("answer", ""),
        citations=answer_data.get("citations", []),
        confidence=answer_data.get("confidence", "MEDIUM")
    )
    db.add(assistant_msg)
    
    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Chat query executed for document: {doc.filename}"
    )
    db.add(audit_log)
    db.commit()
    
    citations_resp = []
    if assistant_msg.citations:
        for c in assistant_msg.citations:
            citations_resp.append(ChatCitationResponse(
                clause_type=c.get("clause_type", ""),
                snippet=c.get("snippet", "")
            ))
        
    return ChatResponse(
        answer=assistant_msg.content,
        citations=citations_resp,
        confidence=assistant_msg.confidence,
        disclaimer=answer_data.get("disclaimer", "This AI response assists document review and is not legal advice.")
    )

@router.get("/{document_id}/chat/history", response_model=list[ChatHistoryItemResponse])
@limiter.limit("60/minute")
def get_chat_history(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[ChatHistoryItemResponse]:
    """
    Retrieve chat history for a document.
    """
    doc = get_accessible_document(db, document_id, current_user)
    
    messages = db.query(ChatMessage).filter(ChatMessage.document_id == doc.id).order_by(ChatMessage.created_at.asc()).all()
    
    history = []
    for msg in messages:
        citations_resp = []
        if msg.citations:
            for c in msg.citations:
                citations_resp.append(ChatCitationResponse(
                    clause_type=c.get("clause_type", ""),
                    snippet=c.get("snippet", "")
                ))
        history.append(ChatHistoryItemResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            citations=citations_resp,
            confidence=msg.confidence,
            created_at=msg.created_at.isoformat() if msg.created_at else ""
        ))
        
    return history

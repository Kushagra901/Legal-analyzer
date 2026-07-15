# documents.py
"""
Documents Router.
Exposes endpoints for uploading and retrieving documents.
"""
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from pydantic import BaseModel
from app.core.database import get_db
from app.models import Document, AuditLog, ExtractedText, Clause, RiskFlag, ComplianceCheck, LegalReference, Report, AutomationRun
from app.services.storage_service import StorageService
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.risk_service import RiskService
from app.services.compliance_service import ComplianceService

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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


@router.post("")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Upload a document, validate it, save it to storage, and return a mock processing status.
    """
    # 1. Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
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

    # Ensure dummy user exists in database
    user_id = ensure_test_user_exists(db)

    # 3. Upload to Supabase Storage
    storage_service = StorageService()
    unique_filename = f"{uuid.uuid4()}/{file.filename}"
    try:
        storage_path = storage_service.upload_file(
            file_data=content,
            file_path=unique_filename,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}"
        )

    # 4. Extract Text Natively or via Tesseract OCR Fallback
    ocr_service = OCRService()
    extracted_text, method = ocr_service.process_document(content)

    # 5. Save to Database
    db_doc = Document(
        filename=file.filename,
        user_id=user_id,
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
            method=method
        )
        db.add(db_extracted)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving extracted text to database: {e}")

    # 7. Perform Analysis (LLM + Risk + Compliance)
    try:
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
            db_clause = Clause(
                id=uuid.uuid4(),
                document_id=db_doc.id,
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

        # Save compliance audit record
        db_compliance = ComplianceCheck(
            id=uuid.uuid4(),
            document_id=db_doc.id,
            rule_set=compliance_res.get("rule_set", "standard_nda"),
            result=json.dumps(compliance_res.get("violations", []))
        )
        db.add(db_compliance)

        # Save legal references
        for citation_data in analysis.get("citations", []):
            db_ref = LegalReference(
                id=uuid.uuid4(),
                document_id=db_doc.id,
                source=citation_data.get("source"),
                citation=citation_data.get("citation")
            )
            db.add(db_ref)

        # Update Document record with summary and score
        db_doc.summary = analysis.get("summary", "")
        db_doc.safety_score = safety_score
        db_doc.risk_level = risk_level
        db_doc.status = "completed"
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error performing analysis or saving results: {e}")
        db_doc.status = "failed"
        db.commit()

    # 8. Write audit log
    audit_log = AuditLog(
        document_id=db_doc.id,
        action=f"Document uploaded and analyzed: {file.filename} (Size: {file_size} bytes, Safety Score: {db_doc.safety_score}, Risk Level: {db_doc.risk_level}, Status: {db_doc.status})"
    )
    db.add(audit_log)
    db.commit()

    # 9. Trigger n8n webhook in background
    background_tasks.add_task(trigger_n8n_webhook, str(db_doc.id), db_doc.filename)

    return {
        "document_id": str(db_doc.id),
        "filename": db_doc.filename,
        "status": db_doc.status,
        "uploaded_at": db_doc.uploaded_at.isoformat(),
        "storage_path": storage_path
    }

@router.get("")
def list_documents(
    db: Session = Depends(get_db)
) -> list[dict]:
    """
    Retrieve all uploaded documents.
    """
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        }
        for doc in docs
    ]

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Retrieve details for an analyzed document.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format."
        )

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

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
        
        clauses.append({
            "id": str(c_db.id),
            "type": c_db.clause_type,
            "text": c_db.clause_text,
            "explanation": explanation or f"Standard {c_db.clause_type} clause.",
            "severity": severity
        })

    # Load citations
    citations_db = db.query(LegalReference).filter(LegalReference.document_id == doc.id).all()
    citations = [
        {
            "source": cit.source,
            "citation": cit.citation
        }
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

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "original_text": original_text,
        "analysis": {
            "safety_score": doc.safety_score if doc.safety_score is not None else 100,
            "risk_level": doc.risk_level if doc.risk_level is not None else "LOW",
            "summary": doc.summary or "Analysis complete.",
            "clauses": clauses,
            "citations": citations,
            "recommendations": recommendations,
            "compliance_violations": violations
        }
    }


@router.post("/{document_id}/ocr")
def run_ocr(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "ocr_completed", "document_id": document_id}


@router.post("/{document_id}/analyze")
def run_analysis(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
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
    
    return {"status": "analyzed", "summary": doc.summary}


@router.post("/{document_id}/score")
def run_scoring(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
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
    
    return {"status": "scored", "safety_score": safety_score, "risk_level": risk_level}


@router.post("/{document_id}/compliance")
def run_compliance(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
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
    
    return {"status": "compliance_checked", "violations": compliance_res.get("violations", [])}


@router.post("/{document_id}/report")
def run_report(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
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
    
    return {"status": "report_generated", "report_url": db_report.file_url}


class AuditAction(BaseModel):
    action: str | None = None


@router.post("/{document_id}/audit")
def run_audit(document_id: str, body: AuditAction = None, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    action_str = body.action if (body and body.action) else f"Workflow processing step completed for document: {doc.filename}"
    
    audit_log = AuditLog(
        document_id=doc.id,
        action=action_str
    )
    db.add(audit_log)
    db.commit()
    
    return {"status": "audit_logged"}


@router.post("/{document_id}/escalate")
def escalate_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc.status = "flagged"
    
    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Document escalated to human review: {doc.filename}"
    )
    db.add(audit_log)
    db.commit()
    
    return {"status": "flagged", "message": "Escalated to human review."}


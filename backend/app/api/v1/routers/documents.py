# documents.py
"""
Documents Router.
Exposes endpoints for uploading and retrieving documents.
"""
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.models import Document, AuditLog
from app.services.storage_service import StorageService
from app.services.ocr_service import OCRService

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

@router.post("")
async def upload_document(
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
        db.execute(
            text("""
                INSERT INTO public.extracted_text (id, document_id, content, method)
                VALUES (:id, :document_id, :content, :method)
            """),
            {
                "id": str(uuid.uuid4()),
                "document_id": db_doc.id,
                "content": extracted_text,
                "method": method
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving extracted text to database: {e}")

    # 7. Write audit log
    audit_log = AuditLog(
        document_id=db_doc.id,
        action=f"Document uploaded: {file.filename} (Size: {file_size} bytes, Extracted: {len(extracted_text)} chars, Method: {method})"
    )
    db.add(audit_log)
    db.commit()

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

    # Automatically complete processing for mock/demo purposes
    if doc.status == "processing":
        doc.status = "completed"
        db.commit()
        db.refresh(doc)

    # Try to load real extracted text from database
    try:
        extracted_record = db.execute(
            text("SELECT content, method FROM public.extracted_text WHERE document_id = :doc_id"),
            {"doc_id": doc.id}
        ).first()
    except Exception as e:
        extracted_record = None
        print(f"Error querying extracted text: {e}")
    
    if extracted_record and extracted_record[0]:
        original_text = extracted_record[0]
        extraction_method = extracted_record[1]
    else:
        original_text = (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Mutual Non-Disclosure Agreement (the \"Agreement\") is entered into by and between the parties to explore a potential business relationship of mutual interest.\n\n"
            "1. Purpose. The parties wish to explore a potential business relationship of mutual interest...\n\n"
            "2. Confidential Information. \"Confidential Information\" means any information or materials disclosed by one party to the other party that is marked as confidential or should reasonably be understood to be confidential.\n\n"
            "3. Confidentiality Obligations. The Receiving Party agrees: (a) to hold the Disclosing Party's Confidential Information in strict confidence and to take reasonable precautions to protect such Confidential Information.\n\n"
            "4. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES, ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT.\n\n"
            "5. Governing Law & Jurisdiction. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles."
        )
        extraction_method = "mock"

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "original_text": original_text,
        "analysis": {
            "safety_score": 92,
            "risk_level": "LOW",
            "summary": "Standard mutual agreement. All obligations of confidentiality are reciprocal and conform to general commercial standards. Minimal legal exposure detected.",
            "clauses": [
                {
                    "id": "clause_1",
                    "type": "Confidentiality Obligations",
                    "text": "The Receiving Party agrees: (a) to hold the Disclosing Party's Confidential Information in strict confidence and to take reasonable precautions to protect such Confidential Information.",
                    "explanation": "Confidentiality obligations are reciprocal and standard. Both parties are equally bound.",
                    "severity": "LOW"
                },
                {
                    "id": "clause_2",
                    "type": "Limitation of Liability",
                    "text": "NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES, ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT.",
                    "explanation": "Reciprocal waiver of consequential damages. Standard risk mitigation.",
                    "severity": "LOW"
                },
                {
                    "id": "clause_3",
                    "type": "Governing Law & Jurisdiction",
                    "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles.",
                    "explanation": "Delaware is a standard neutral jurisdiction for commercial agreements.",
                    "severity": "LOW"
                }
            ],
            "citations": [
                {
                    "source": "Del. Code Ann. tit. 6, § 2707",
                    "citation": "Governs enforceability of choice of law provisions in commercial contracts."
                },
                {
                    "source": "Restatement (Second) of Contracts § 187",
                    "citation": "Law of the state chosen by the parties to govern their contractual rights and duties will be applied."
                }
            ],
            "recommendations": [
                "Ensure Wilmington, Delaware is an acceptable jurisdiction for your operations before formal execution.",
                "No amendments are strictly necessary, as standard mutual clauses protect both parties adequately."
            ]
        }
    }


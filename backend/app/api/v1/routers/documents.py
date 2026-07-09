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

    # 4. Save to Database
    db_doc = Document(
        filename=file.filename,
        user_id=user_id,
        status="processing"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # 5. Write audit log
    audit_log = AuditLog(
        document_id=db_doc.id,
        action=f"Document uploaded: {file.filename} (Size: {file_size} bytes)"
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

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at.isoformat()
    }

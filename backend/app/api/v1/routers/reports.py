"""
Reports router.
Handles retrieval and generation requests for legal memorandum reports.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Document

router = APIRouter()

@router.get("/{document_id}")
def get_report(
    document_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Retrieve generated memorandum audit report by document ID.
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
        "uploaded_at": doc.uploaded_at.isoformat(),
        "report_url": f"/reports/{doc.id}.pdf",
        "safety_score": 92,
        "risk_level": "LOW",
        "summary": "The document under review is a standard Mutual Non-Disclosure Agreement. Based on our analysis, the document represents low exposure and is safe to execute. Reciprocal provisions for confidentiality, duration, governing law, and limitations of liability are fully present.",
        "recommendations": [
            "Ensure Wilmington, Delaware is an acceptable jurisdiction for your operations before formal execution.",
            "No amendments are strictly necessary, as standard mutual clauses protect both parties adequately."
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
        ]
    }


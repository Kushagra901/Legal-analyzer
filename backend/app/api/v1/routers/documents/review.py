"""
Review router for document clauses.
Handles persisting and retrieving attorney clause review decisions and notes.
"""

import datetime
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import AuditLog, Clause, ClauseReview, User
from app.models.schemas import ClauseReviewCreate, ClauseReviewResponse

logger = logging.getLogger(__name__)

router = APIRouter()



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

    logger.info(
        "Recorded clause review for document %s, clause %s: decision=%s",
        doc.id,
        clause.id,
        body.decision,
    )

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

"""
Administration router.
Handles audit logs and pipeline monitoring endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.models import AuditLog, Document, User
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[dict[str, str]]:
    """
    Retrieve historical audit logs for admin overview.
    Enforces administrator access control.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )

    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
    results = []

    for log in logs:
        user_email = "system"
        if log.document_id:
            doc = db.query(Document).filter(Document.id == log.document_id).first()
            if doc:
                user_record = db.query(User).filter(User.id == doc.user_id).first()
                if user_record:
                    user_email = user_record.email

        results.append({
            "id": str(log.id),
            "action": log.action,
            "document_id": str(log.document_id) if log.document_id else "",
            "user": user_email,
            "timestamp": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        })

    return results

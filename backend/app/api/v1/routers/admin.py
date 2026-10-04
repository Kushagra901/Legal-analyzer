"""
Administration router.
Handles audit logs and pipeline monitoring endpoints.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import AuditLog, Document, User
from app.models.schemas import AuditLogItemResponse, PaginatedAuditLogList

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that verifies the current user has the 'admin' role.
    Raises 403 Forbidden HTTP exception if non-admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    return current_user


@router.get("/audit-logs", response_model=PaginatedAuditLogList)
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=100, description="Max audit logs to return"),
    offset: int = Query(default=0, ge=0, description="Number of audit logs to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PaginatedAuditLogList:
    """
    Retrieve historical audit logs for admin overview with pagination.
    Enforces administrator access control via require_admin dependency.
    """
    total = db.query(AuditLog).count()
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    results = []

    for log in logs:
        user_email = "system"
        if log.document_id:
            doc = db.query(Document).filter(Document.id == log.document_id).first()
            if doc:
                user_record = db.query(User).filter(User.id == doc.user_id).first()
                if user_record:
                    user_email = user_record.email

        results.append(AuditLogItemResponse(
            id=str(log.id),
            action=log.action,
            document_id=str(log.document_id) if log.document_id else "",
            user=user_email,
            timestamp=log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else ""
        ))

    return PaginatedAuditLogList(
        items=results,
        total=total,
        limit=limit,
        offset=offset,
    )

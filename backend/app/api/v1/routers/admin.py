"""
Administration router.
Handles audit logs and pipeline monitoring endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/audit-logs")
def get_audit_logs() -> list[dict[str, str]]:
    """
    Retrieve historical audit logs for admin overview.

    Returns:
        list[dict[str, str]]: A list of audit logs.
    """
    return [
        {
            "id": "log_01239",
            "action": "UPLOAD_DOCUMENT",
            "document_id": "doc_001",
            "user": "kushal@company.com",
            "timestamp": "2026-07-08 11:39:00",
        }
    ]

"""
Reports router.
Handles retrieval and generation requests for legal memorandum reports.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{document_id}")
def get_report(document_id: str) -> dict[str, str]:
    """
    Retrieve generated memorandum audit report by document ID.

    Args:
        document_id (str): The unique ID of the document.

    Returns:
        dict[str, str]: Stated report details.
    """
    return {"document_id": document_id, "report_url": f"/reports/{document_id}.pdf"}

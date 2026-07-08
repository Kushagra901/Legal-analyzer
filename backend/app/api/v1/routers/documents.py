"""
Documents router.
Handles upload, search, detail retrieval, and analysis actions for legal contracts.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/")
def upload_document() -> dict[str, str]:
    """
    Ingest a new document for processing.

    Returns:
        dict[str, str]: Response confirming file upload trigger.
    """
    return {"message": "document upload triggered"}


@router.get("/{document_id}")
def get_document(document_id: str) -> dict[str, str]:
    """
    Retrieve details for an analyzed document.

    Args:
        document_id (str): The unique ID of the document.

    Returns:
        dict[str, str]: Stated document details.
    """
    return {"document_id": document_id, "status": "completed"}

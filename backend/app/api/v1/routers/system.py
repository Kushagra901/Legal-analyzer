"""
system.py
System and infrastructure operational status router.
Exposes health, diagnostics, and service integration checks.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from app.services.ollama_service import OllamaService

router = APIRouter()


class OllamaStatusResponse(BaseModel):
    """Schema for Ollama service availability and operational status."""
    model_config = ConfigDict(extra="ignore")

    healthy: bool
    base_url: str
    model: str
    document_id: str | None = None


@router.get("/ollama-status", response_model=OllamaStatusResponse)
def get_ollama_status(
    document_id: str | None = Query(None, description="Optional document ID echoed back for workflow state propagation")
) -> OllamaStatusResponse:
    """
    Exposes the Ollama service reachability and operational status check.

    Returns:
        OllamaStatusResponse: Boolean indicator of whether Ollama is reachable,
        the configured base URL, model, and optional propagated document_id.
    """
    is_healthy = OllamaService.check_health()
    return OllamaStatusResponse(
        healthy=is_healthy,
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        document_id=document_id,
    )

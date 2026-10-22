"""
Models package initialization.
Contains database schema tables, pydantic entities, and ORM objects.
"""
from app.models.database_models import (
    GUID,
    AuditLog,
    AutomationRun,
    ChatMessage,
    Clause,
    ClauseReview,
    ComplianceCheck,
    DeepExtraction,
    Document,
    DocumentChunk,
    ExtractedText,
    LegalReference,
    Notification,
    Organization,
    Report,
    RiskFlag,
    User,
    VectorType,
)
from app.models.schemas import ClauseCategory, clause_category

__all__ = [
    "Organization",
    "User",
    "Document",
    "DocumentChunk",
    "AuditLog",
    "ExtractedText",
    "Clause",
    "RiskFlag",
    "ComplianceCheck",
    "LegalReference",
    "Report",
    "Notification",
    "AutomationRun",
    "ClauseReview",
    "ChatMessage",
    "DeepExtraction",
    "GUID",
    "VectorType",
    "ClauseCategory",
    "clause_category",
]


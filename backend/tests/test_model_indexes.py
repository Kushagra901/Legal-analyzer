"""
Unit tests for foreign key and filtering column database indexes.
Validates DATA-DB-004-INDEX-OPTIMIZATION requirements.
"""

from app.models.database_models import (
    AuditLog,
    AutomationRun,
    ChatMessage,
    Clause,
    ClauseReview,
    ComplianceCheck,
    Document,
    DocumentChunk,
    ExtractedText,
    LegalReference,
    Report,
    RiskFlag,
)


def test_model_foreign_key_and_filter_column_indexes():
    """Verify that index=True is set on all required foreign key and filtering columns."""
    expected_indexes = [
        (Document, "user_id"),
        (Clause, "document_id"),
        (RiskFlag, "clause_id"),
        (ExtractedText, "document_id"),
        (ComplianceCheck, "document_id"),
        (LegalReference, "document_id"),
        (Report, "document_id"),
        (AuditLog, "document_id"),
        (AutomationRun, "document_id"),
        (ClauseReview, "document_id"),
        (ClauseReview, "clause_id"),
        (DocumentChunk, "document_id"),
        (ChatMessage, "document_id"),
        (ChatMessage, "conversation_id"),
    ]

    for model, column_name in expected_indexes:
        column = getattr(model, column_name)
        assert column.index is True, f"Expected {model.__name__}.{column_name} to have index=True"


def test_table_indexes_in_metadata():
    """Verify that SQLAlchemy table metadata contains the generated indexes."""
    from app.core.database import Base

    expected_table_columns = {
        "documents": {"user_id"},
        "clauses": {"document_id"},
        "risk_flags": {"clause_id"},
        "extracted_text": {"document_id"},
        "compliance_checks": {"document_id"},
        "legal_references": {"document_id"},
        "reports": {"document_id"},
        "audit_logs": {"document_id"},
        "automation_runs": {"document_id"},
        "clause_reviews": {"document_id", "clause_id"},
        "document_chunks": {"document_id"},
        "chat_messages": {"document_id", "conversation_id"},
    }

    for table_name, indexed_cols in expected_table_columns.items():
        assert table_name in Base.metadata.tables, f"Table {table_name} missing from metadata"
        table = Base.metadata.tables[table_name]
        table_index_cols = {col.name for idx in table.indexes for col in idx.columns}
        for col_name in indexed_cols:
            assert col_name in table_index_cols, (
                f"Column {col_name} on table {table_name} not found among indexed columns: {table_index_cols}"
            )

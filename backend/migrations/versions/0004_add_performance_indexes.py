"""add performance indexes

Revision ID: 0004_add_performance_indexes
Revises:
Create Date: 2026-07-29

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004_add_performance_indexes'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('idx_documents_user_id', 'documents', ['user_id'], unique=False)
    op.create_index('idx_documents_status', 'documents', ['status'], unique=False)
    op.create_index('idx_clauses_document_id', 'clauses', ['document_id'], unique=False)
    op.create_index('idx_risk_flags_clause_id', 'risk_flags', ['clause_id'], unique=False)
    op.create_index('idx_audit_logs_document_id', 'audit_logs', ['document_id'], unique=False)
    op.create_index('idx_compliance_checks_document_id', 'compliance_checks', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_compliance_checks_document_id', table_name='compliance_checks')
    op.drop_index('idx_audit_logs_document_id', table_name='audit_logs')
    op.drop_index('idx_risk_flags_clause_id', table_name='risk_flags')
    op.drop_index('idx_clauses_document_id', table_name='clauses')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_user_id', table_name='documents')

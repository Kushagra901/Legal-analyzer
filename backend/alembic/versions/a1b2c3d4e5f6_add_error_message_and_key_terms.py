"""add_error_message_and_key_terms

Revision ID: a1b2c3d4e5f6
Revises: 2e1482525d09
Create Date: 2026-10-17 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "2e1482525d09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add error_message and key_terms columns."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
        op.add_column("documents", sa.Column("key_terms", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    else:
        op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
        op.add_column("documents", sa.Column("key_terms", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "key_terms")
    op.drop_column("documents", "error_message")

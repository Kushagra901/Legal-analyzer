# database_models.py
"""
Database Models.
Defines SQLAlchemy ORM mappings for the core database schema.
"""
import json
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.types import CHAR, TypeDecorator

from app.core.database import Base


class VectorType(TypeDecorator):
    """
    Platform-independent Vector type for 768-dim embeddings.
    Uses pgvector's Vector in PostgreSQL, and Text (JSON) in SQLite.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 768, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(Vector(self.dim))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return list(value) if hasattr(value, '__iter__') and not isinstance(value, str) else value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36) to prevent numeric conversion on SQLite.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class Organization(Base):
    """
    SQLAlchemy model representing the organizations table.
    """
    __tablename__ = "organizations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name: str = Column(String(255), nullable=False)
    plan: str = Column(String(50), nullable=False, default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    """
    SQLAlchemy model representing the users table.
    """
    __tablename__ = "users"

    id = Column(GUID, primary_key=True)
    org_id = Column(GUID, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    email: str = Column(String(255), unique=True, nullable=False)
    role: str = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Document(Base):
    """
    SQLAlchemy model representing the documents table.
    """
    __tablename__ = "documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename: str = Column(String(255), nullable=False)
    status: str = Column(String(50), nullable=False, default="pending")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    summary: str = Column(Text, nullable=True)
    safety_score: int = Column(Integer, nullable=True)
    risk_level: str = Column(String(50), nullable=True)
    parties = Column(JSON, nullable=True)
    key_dates = Column(JSON, nullable=True)
    missing_sections = Column(JSON, nullable=True)
    document_overview: str = Column(Text, nullable=True)
    plain_english_summary: str = Column(Text, nullable=True)


class AuditLog(Base):
    """
    SQLAlchemy model representing the audit_logs table.
    """
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    action: str = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExtractedText(Base):
    """
    SQLAlchemy model representing the extracted_text table.
    """
    __tablename__ = "extracted_text"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content: str = Column(Text, nullable=False)
    method: str = Column(String(100), nullable=False)
    parsing_confidence: float = Column(Float, nullable=False, default=1.0)


class Clause(Base):
    """
    SQLAlchemy model representing the clauses table.
    """
    __tablename__ = "clauses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    clause_type: str = Column(String(100), nullable=False)
    clause_text: str = Column(Text, nullable=False)
    embedding = Column(Vector, nullable=True)
    confidence_score: float = Column(Float, nullable=True)
    category: str = Column(String(255), nullable=True)


class RiskFlag(Base):
    """
    SQLAlchemy model representing the risk_flags table.
    """
    __tablename__ = "risk_flags"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    clause_id = Column(GUID, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False)
    severity: str = Column(String(50), nullable=False)
    explanation: str = Column(Text, nullable=False)


class ComplianceCheck(Base):
    """
    SQLAlchemy model representing the compliance_checks table.
    """
    __tablename__ = "compliance_checks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    rule_set: str = Column(String(100), nullable=False)
    result: str = Column(Text, nullable=False)


class LegalReference(Base):
    """
    SQLAlchemy model representing the legal_references table.
    """
    __tablename__ = "legal_references"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    source: str = Column(String(255), nullable=False)
    citation: str = Column(String(255), nullable=False)


class Report(Base):
    """
    SQLAlchemy model representing the reports table.
    """
    __tablename__ = "reports"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    format: str = Column(String(50), nullable=False)
    file_url: str = Column(Text, nullable=False)


class Notification(Base):
    """
    SQLAlchemy model representing the notifications table.
    """
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: str = Column(String(100), nullable=False)
    read: bool = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AutomationRun(Base):
    """
    SQLAlchemy model representing the automation_runs table.
    """
    __tablename__ = "automation_runs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    workflow_name: str = Column(String(255), nullable=False)
    status: str = Column(String(100), nullable=False)
    retry_count: int = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClauseReview(Base):
    """
    SQLAlchemy model representing the clause_reviews table.
    Tracks attorney review decisions and notes for individual clauses.
    """
    __tablename__ = "clause_reviews"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    clause_id = Column(GUID, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    decision: str = Column(String(50), nullable=False, default="pending")
    note: str = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentChunk(Base):
    """
    SQLAlchemy model representing the document_chunks table.
    Stores ~800-character overlapping chunks and their 768-dim embeddings.
    """
    __tablename__ = "document_chunks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(VectorType(768), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatMessage(Base):
    """
    SQLAlchemy model representing the chat_messages table.
    Stores document-scoped conversational Q&A messages.
    """
    __tablename__ = "chat_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    conversation_id = Column(GUID, nullable=False, default=uuid.uuid4)
    role: str = Column(String(20), nullable=False)
    content: str = Column(Text, nullable=False)
    citations = Column(JSON, default=list)
    confidence: str = Column(String(10), default="MEDIUM")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeepExtraction(Base):
    """
    SQLAlchemy model representing the deep_extractions table.
    Stores structured deep extraction results for a document.
    """
    __tablename__ = "deep_extractions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    deal_terms = Column(JSON, default=dict)
    obligations = Column(JSON, default=list)
    risk_flags = Column(JSON, default=list)
    missing_protections = Column(JSON, default=list)
    redline_suggestions = Column(JSON, default=list)
    executive_summary: str = Column(Text, nullable=True)
    confidence: str = Column(String(10), default="MEDIUM")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


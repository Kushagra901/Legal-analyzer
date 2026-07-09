# database_models.py
"""
Database Models.
Defines SQLAlchemy ORM mappings for the core database schema.
"""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.core.database import Base

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


class AuditLog(Base):
    """
    SQLAlchemy model representing the audit_logs table.
    """
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    action: str = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

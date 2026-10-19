"""
Audit Service.
Handles logging and persisting document workflow and audit trail events.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service class responsible for recording document and workflow audit events.
    """

    @staticmethod
    def log_event(
        document_id: str | uuid.UUID,
        event_type: str,
        db: Session | None = None,
        details: str | None = None
    ) -> AuditLog | None:
        """
        Record a structured audit log entry for a document action.

        Args:
            document_id: Unique UUID identifier of the document.
            event_type: The action identifier or event label (e.g., 'pipeline_completed').
            db: Optional active SQLAlchemy session. If None, a new session is managed.
            details: Optional extra description to append to the action string.

        Returns:
            The created AuditLog instance, or None if the write failed.
        """
        doc_uuid = uuid.UUID(str(document_id)) if not isinstance(document_id, uuid.UUID) else document_id
        action_text = f"{event_type}: {details}" if details else str(event_type)

        should_close = False
        session = db
        if session is None:
            session = SessionLocal()
            should_close = True

        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                action=action_text
            )
            session.add(audit_log)
            session.commit()
            session.refresh(audit_log)
            logger.info("Audit log recorded for document %s: %s", doc_uuid, action_text)
            return audit_log
        except Exception as e:
            session.rollback()
            logger.warning("Failed to record audit log for document %s: %s", doc_uuid, e)
            return None
        finally:
            if should_close:
                session.close()


audit_service = AuditService()

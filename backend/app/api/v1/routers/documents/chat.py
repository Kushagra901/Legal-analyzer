"""
Chat router for document Q&A.
Handles vector similarity retrieval, grounded Gemini Q&A, and chat message history.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import (
    AuditLog,
    ChatMessage,
    DocumentChunk,
    ExtractedText,
    User,
)
from app.models.schemas import (
    ChatCitationResponse,
    ChatHistoryItemResponse,
    ChatRequest,
    ChatResponse,
    SourceChunkResponse,
)
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()



@router.post("/{document_id}/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
def chat_with_document(
    request: Request,
    document_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """
    Chat with a document using 768-dim vector similarity search over document_chunks
    and grounded Gemini Q&A.
    """
    doc = get_accessible_document(db, document_id, current_user)

    question = body.question or body.query
    if not question or not question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty.")

    embedding_service = EmbeddingService()

    # 1. Ensure document has chunks; if not yet chunked, chunk it now
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    if chunk_count == 0:
        extracted_text_obj = db.query(ExtractedText).filter(ExtractedText.document_id == doc.id).first()
        extracted_text = extracted_text_obj.content if extracted_text_obj else ""
        if extracted_text:
            embedding_service.chunk_and_embed_document(doc.id, extracted_text, db)

    # 2. Run vector similarity search against THIS document's chunks ONLY (top 5)
    similar_chunks_with_scores = embedding_service.search_similar_chunks(
        document_id=doc.id,
        query_text=question,
        db=db,
        top_k=5
    )

    source_chunks_resp = [
        SourceChunkResponse(
            chunk_id=str(c.id),
            chunk_index=c.chunk_index,
            chunk_text=c.chunk_text,
            similarity=round(score, 4) if score is not None else None
        )
        for c, score in similar_chunks_with_scores
    ]

    chunks_data = [
        {"chunk_id": str(c.id), "chunk_index": c.chunk_index, "chunk_text": c.chunk_text}
        for c, _ in similar_chunks_with_scores
    ]

    # 3. Grounded Q&A via Gemini using the retrieved chunks
    chat_service = ChatService()
    answer_data = chat_service.answer_question_with_chunks(
        question=question,
        chunks=chunks_data,
        document_metadata={"filename": doc.filename, "document_id": str(doc.id)}
    )

    conv_id = uuid.UUID(body.conversation_id) if body.conversation_id else uuid.uuid4()

    # 4. Save both user question and assistant answer to chat_messages
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=current_user.id,
        conversation_id=conv_id,
        role="user",
        content=question
    )
    db.add(user_msg)

    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        document_id=doc.id,
        user_id=current_user.id,
        conversation_id=conv_id,
        role="assistant",
        content=answer_data.get("answer", ""),
        citations=answer_data.get("citations", []),
        confidence=answer_data.get("confidence", "MEDIUM")
    )
    db.add(assistant_msg)

    audit_log = AuditLog(
        document_id=doc.id,
        action=f"Vector chat query executed for document: {doc.filename}"
    )
    db.add(audit_log)
    db.commit()

    logger.info("Executed vector chat query for document %s", doc.id)

    citations_resp = []
    if assistant_msg.citations:
        for c in assistant_msg.citations:
            citations_resp.append(ChatCitationResponse(
                clause_type=c.get("clause_type", "Document Excerpt"),
                snippet=c.get("snippet", "")
            ))

    return ChatResponse(
        answer=assistant_msg.content,
        source_chunks=source_chunks_resp,
        citations=citations_resp,
        confidence=assistant_msg.confidence,
        disclaimer=answer_data.get("disclaimer", "This AI response assists document review and is not legal advice.")
    )


@router.get("/{document_id}/chat/history", response_model=list[ChatHistoryItemResponse])
@limiter.limit("60/minute")
def get_chat_history(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[ChatHistoryItemResponse]:
    """
    Retrieve chat history for a document.
    """
    doc = get_accessible_document(db, document_id, current_user)

    messages = db.query(ChatMessage).filter(ChatMessage.document_id == doc.id).order_by(ChatMessage.created_at.asc()).all()

    history = []
    for msg in messages:
        citations_resp = []
        if msg.citations:
            for c in msg.citations:
                citations_resp.append(ChatCitationResponse(
                    clause_type=c.get("clause_type", ""),
                    snippet=c.get("snippet", "")
                ))
        history.append(ChatHistoryItemResponse(
            id=str(msg.id),
            role=msg.role,
            content=msg.content,
            citations=citations_resp,
            confidence=msg.confidence,
            created_at=msg.created_at.isoformat() if msg.created_at else ""
        ))

    return history

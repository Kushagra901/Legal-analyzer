-- Migration: 0005_add_chat_messages.sql
-- Adds chat_messages table for document-scoped conversational Q&A

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    confidence VARCHAR(10) DEFAULT 'MEDIUM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_document ON public.chat_messages(document_id);
CREATE INDEX idx_chat_messages_conversation ON public.chat_messages(conversation_id);

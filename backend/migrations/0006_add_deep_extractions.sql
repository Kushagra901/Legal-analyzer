-- Migration: 0006_add_deep_extractions.sql
-- Adds deep_extractions table for structured deal terms, obligations, and redlines

CREATE TABLE IF NOT EXISTS public.deep_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    deal_terms JSONB DEFAULT '{}',
    obligations JSONB DEFAULT '[]',
    risk_flags JSONB DEFAULT '[]',
    missing_protections JSONB DEFAULT '[]',
    redline_suggestions JSONB DEFAULT '[]',
    executive_summary TEXT,
    confidence VARCHAR(10) DEFAULT 'MEDIUM',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id)
);

CREATE INDEX idx_deep_extractions_document ON public.deep_extractions(document_id);

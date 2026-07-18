-- 0002_add_document_clause_columns.sql
-- Migration to add extra columns on documents and clauses tables

ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS parties JSONB,
ADD COLUMN IF NOT EXISTS key_dates JSONB,
ADD COLUMN IF NOT EXISTS missing_sections JSONB,
ADD COLUMN IF NOT EXISTS document_overview TEXT,
ADD COLUMN IF NOT EXISTS plain_english_summary TEXT;

ALTER TABLE public.clauses 
ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS category VARCHAR(255);

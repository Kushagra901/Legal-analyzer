-- 0010_add_error_message_and_key_terms.sql
-- Migration to add error_message and key_terms columns to documents table

ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS key_terms JSONB;

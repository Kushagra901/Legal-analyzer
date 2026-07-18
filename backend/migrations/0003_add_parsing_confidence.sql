-- 0003_add_parsing_confidence.sql
-- Migration to add parsing_confidence column on extracted_text table

ALTER TABLE public.extracted_text
ADD COLUMN IF NOT EXISTS parsing_confidence DOUBLE PRECISION DEFAULT 1.0;

-- 0001_initial_schema.sql
-- Database Schema for Legal Analyzer App

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Organizations table
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Users table (profile table linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT fk_users_auth FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- 3. Documents table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    summary TEXT,
    safety_score INTEGER,
    risk_level VARCHAR(50)
);

-- 4. Extracted Text table
CREATE TABLE IF NOT EXISTS public.extracted_text (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    method VARCHAR(100) NOT NULL
);

-- 5. Clauses table (with vector embedding column for pgvector)
CREATE TABLE IF NOT EXISTS public.clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    clause_type VARCHAR(100) NOT NULL,
    clause_text TEXT NOT NULL,
    embedding vector(1536)
);

-- 6. Risk Flags table
CREATE TABLE IF NOT EXISTS public.risk_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID NOT NULL REFERENCES public.clauses(id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL,
    explanation TEXT NOT NULL
);

-- 7. Compliance Checks table
CREATE TABLE IF NOT EXISTS public.compliance_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    rule_set VARCHAR(100) NOT NULL,
    result TEXT NOT NULL
);

-- 8. Legal References table
CREATE TABLE IF NOT EXISTS public.legal_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    citation VARCHAR(255) NOT NULL
);

-- 9. Reports table
CREATE TABLE IF NOT EXISTS public.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    format VARCHAR(50) NOT NULL,
    file_url TEXT NOT NULL
);

-- 10. Notifications table
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 11. Audit Logs table (tracks user actions)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.documents(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 12. Automation Runs table
CREATE TABLE IF NOT EXISTS public.automation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    workflow_name VARCHAR(255) NOT NULL,
    status VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for performance and constraints
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_clauses_document_id ON public.clauses(document_id);
CREATE INDEX IF NOT EXISTS idx_risk_flags_clause_id ON public.risk_flags(clause_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_document_id_created_at ON public.audit_logs(document_id, created_at);

-- Idempotency unique key for automation_runs (document_id + workflow_name)
CREATE UNIQUE INDEX IF NOT EXISTS idx_automation_runs_doc_workflow ON public.automation_runs(document_id, workflow_name);

-- pgvector Index (HNSW for high performance)
CREATE INDEX IF NOT EXISTS idx_clauses_embedding ON public.clauses USING hnsw (embedding vector_cosine_ops);

-- Grant privileges to anon and authenticated roles for API exposure
GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.organizations TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.documents TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.extracted_text TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.clauses TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.risk_flags TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.compliance_checks TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.legal_references TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.reports TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.notifications TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.audit_logs TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.automation_runs TO anon, authenticated;

-- Ensure document table has summary, safety_score, risk_level if it was already created
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS safety_score INTEGER;
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS risk_level VARCHAR(50);

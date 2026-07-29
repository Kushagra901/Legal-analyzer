CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_clauses_document_id ON public.clauses(document_id);
CREATE INDEX IF NOT EXISTS idx_risk_flags_clause_id ON public.risk_flags(clause_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_document_id ON public.audit_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_document_id ON public.compliance_checks(document_id);

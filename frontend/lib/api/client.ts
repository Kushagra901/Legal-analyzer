/**
 * @file client.ts
 * @description Typed API client for FastAPI backend under /api/v1.
 * Automatically injects Supabase Bearer JWT tokens in Authorization header.
 */

import { createClient as createBrowserSupabase } from "@/lib/supabase/client";

export interface DocumentListItemResponse {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at?: string | null;
  safety_score?: number | null;
  risk_level?: string | null;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at: string;
  storage_path: string;
}

export interface ClauseResponse {
  id?: string;
  type: string;
  text: string;
  risk_level?: string;
  severity?: string;
  explanation?: string;
}


export interface CitationResponse {
  source: string;
  citation: string;
}

export interface AnalysisDetailResponse {
  summary?: string;
  safety_score?: number;
  risk_level?: string;
  clauses?: ClauseResponse[];
  citations?: CitationResponse[];
  compliance_checks?: Array<{
    rule_set: string;
    violations: string[];
  }>;
  extracted_text?: string;
}

export interface DocumentResponse {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at?: string;
  analysis?: AnalysisDetailResponse;
}

export interface ReportResponse {
  document_id: string;
  filename: string;
  summary: string;
  safety_score: number;
  risk_level: string;
  clauses: ClauseResponse[];
  citations: CitationResponse[];
  compliance_checks?: Array<{
    rule_set: string;
    violations: string[];
  }>;
  generated_at?: string;
}

export interface AnalysisStatusResponse {
  status: string;
  message?: string;
  document_id?: string;
  filename?: string;
  safety_score?: number | null;
  risk_level?: string | null;
}

export interface AuditLogItemResponse {
  id: string;
  document_id?: string;
  action: string;
  created_at: string;
}

export interface ClauseReviewResponse {
  id: string;
  clause_id: string;
  document_id: string;
  user_id: string;
  decision: "pending" | "approved" | "redline_flagged" | string;
  note?: string | null;
  reviewed_at: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createBrowserSupabase();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const getDocuments = async (): Promise<DocumentListItemResponse[]> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch documents.");
  }
  return res.json();
};

const uploadDocument = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  const headers = await getAuthHeaders();

  const res = await fetch(`${API_BASE_URL}/api/v1/documents`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload document.");
  }
  return res.json();
};

const getDocument = async (id: string): Promise<DocumentResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${id}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch document analysis.");
  }
  return res.json();
};

const updateClause = async (
  documentId: string,
  clauseId: string,
  payload: { action?: string; clause_text?: string; risk_level?: string }
): Promise<AnalysisStatusResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/audit`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      action: payload.action || `Updated clause ${clauseId}: ${payload.clause_text || ""}`,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update clause.");
  }
  return res.json();
};

const createOrUpdateClauseReview = async (
  documentId: string,
  clauseId: string,
  payload: { decision: string; note?: string }
): Promise<ClauseReviewResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE_URL}/api/v1/documents/${documentId}/clauses/${clauseId}/review`,
    {
      method: "POST",
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit clause review decision.");
  }
  return res.json();
};

const getDocumentReviews = async (
  documentId: string
): Promise<ClauseReviewResponse[]> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${documentId}/reviews`, {
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch document reviews.");
  }
  return res.json();
};

const deleteDocument = async (id: string): Promise<AnalysisStatusResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${id}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete document.");
  }
  return res.json();
};

const getReport = async (id: string): Promise<ReportResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/reports/${id}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch report.");
  }
  return res.json();
};

const getAuditLogs = async (): Promise<AuditLogItemResponse[]> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/admin/audit-logs`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch audit logs.");
  }
  return res.json();
};

const escalateDocument = async (id: string): Promise<AnalysisStatusResponse> => {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/api/v1/documents/${id}/escalate`, {
    method: "POST",
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to escalate document for human review.");
  }
  return res.json();
};

export const apiClient = {
  getDocuments,
  fetchDocuments: getDocuments,
  uploadDocument,
  getDocument,
  fetchDocument: getDocument,
  updateClause,
  createOrUpdateClauseReview,
  getDocumentReviews,
  escalateDocument,
  deleteDocument,
  getReport,
  fetchReport: getReport,
  getAuditLogs,
  fetchAuditLogs: getAuditLogs,
};



/**
 * @file index.ts
 * @description API client wrappers. Includes Supabase Auth Bearer headers.
 */

import { supabase } from "@/lib/supabase";

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const apiClient = {
  fetchDocuments: async () => {
    const headers = await getAuthHeaders();
    const res = await fetch("/api/v1/documents", { headers });
    return res.json();
  },
  fetchDocument: async (id: string) => {
    const headers = await getAuthHeaders();
    const res = await fetch(`/api/v1/documents/${id}`, { headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch document details");
    }
    return res.json();
  },
  fetchReport: async (id: string) => {
    const headers = await getAuthHeaders();
    const res = await fetch(`/api/v1/reports/${id}`, { headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch report details");
    }
    return res.json();
  },
  fetchAuditLogs: async () => {
    const headers = await getAuthHeaders();
    const res = await fetch("/api/v1/admin/audit-logs", { headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch audit logs");
    }
    return res.json();
  },
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const headers = await getAuthHeaders();
    const res = await fetch("/api/v1/documents", {
      method: "POST",
      body: formData,
      headers,
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to upload document");
    }
    return res.json();
  },
};

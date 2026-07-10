/**
 * @file index.ts
 * @description API client wrappers and setup placeholders.
 */

export const apiClient = {
  fetchDocuments: async () => {
    const res = await fetch("/api/v1/documents");
    return res.json();
  },
  fetchDocument: async (id: string) => {
    const res = await fetch(`/api/v1/documents/${id}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch document details");
    }
    return res.json();
  },
  fetchReport: async (id: string) => {
    const res = await fetch(`/api/v1/reports/${id}`);
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch report details");
    }
    return res.json();
  },
  fetchAuditLogs: async () => {
    const res = await fetch("/api/v1/admin/audit-logs");
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to fetch audit logs");
    }
    return res.json();
  },
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/v1/documents", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "Failed to upload document");
    }
    return res.json();
  },
};


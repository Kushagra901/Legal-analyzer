/**
 * @file index.ts
 * @description API client wrappers and setup placeholders.
 */

export const apiClient = {
  fetchDocuments: async () => {
    const res = await fetch("/api/v1/documents");
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


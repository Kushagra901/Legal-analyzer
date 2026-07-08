/**
 * @file index.ts
 * @description API client wrappers and setup placeholders.
 */

export const apiClient = {
  fetchDocuments: async () => {
    const res = await fetch("/api/v1/documents");
    return res.json();
  },
};

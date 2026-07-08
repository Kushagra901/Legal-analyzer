/**
 * @file index.ts
 * @description Custom React hooks placeholder.
 */

import { useState } from "react";

export function useDocumentList() {
  const [documents] = useState([]);
  const loading = false;

  return { documents, loading };
}


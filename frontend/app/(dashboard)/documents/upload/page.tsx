"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function DocumentUploadPage() {
  const router = useRouter();
  const [successDocId, setSuccessDocId] = useState<string | null>(null);

  const handleUploadSuccess = (doc: {
    document_id: string;
    filename: string;
    status: string;
  }) => {
    setSuccessDocId(doc.document_id);
    setTimeout(() => {
      router.push(`/documents/${doc.document_id}`);
    }, 1200);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="border-b border-[var(--border-subtle)] pb-6">
        <h1 className="font-serif text-2xl md:text-3xl font-bold text-[var(--accent-primary)]">
          Upload Contract Document
        </h1>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Select or drag a legal contract (NDA, Master Service Agreement, Employment Agreement, Policy) for first-pass extraction and risk scoring.
        </p>
      </div>

      {/* Upload Dropzone Container */}
      <Card>
        <CardHeader>
          <CardTitle>File Ingestion & Parsing Dropzone</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {successDocId ? (
            <div className="p-6 bg-[var(--risk-low-bg)] border border-[var(--risk-low)] text-[var(--risk-low)] text-xs text-center space-y-2">
              <p className="font-bold text-sm font-serif">Upload and Analysis Completed Successfully</p>
              <p>Redirecting to interactive split-pane results...</p>
            </div>
          ) : (
            <UploadDropzone onUploadSuccess={handleUploadSuccess} />
          )}

          {/* Guidelines & Workflow Specifications */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-[var(--border-subtle)] text-xs">
            <div className="p-3 border border-[var(--border-subtle)] bg-[var(--bg-page)]">
              <h4 className="font-serif font-bold text-[var(--accent-primary)] mb-1">
                Accepted Formats
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                PDF, DOCX, and TXT files up to 10MB in size are processed natively.
              </p>
            </div>

            <div className="p-3 border border-[var(--border-subtle)] bg-[var(--bg-page)]">
              <h4 className="font-serif font-bold text-[var(--accent-primary)] mb-1">
                OCR & Text Extraction
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                Scanned documents automatically trigger Tesseract OCR fallback for text recovery.
              </p>
            </div>

            <div className="p-3 border border-[var(--border-subtle)] bg-[var(--bg-page)]">
              <h4 className="font-serif font-bold text-[var(--accent-primary)] mb-1">
                Structured Analysis
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                Clauses, risk severity flags, precedent citations, and NDA compliance violations are computed instantly.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

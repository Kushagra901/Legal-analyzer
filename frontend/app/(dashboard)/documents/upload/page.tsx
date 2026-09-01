"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiClient, QuickSummaryResponse } from "@/lib/api/client";

export default function DocumentUploadPage() {
  const router = useRouter();
  const [successDocId, setSuccessDocId] = useState<string | null>(null);
  const [quickSummary, setQuickSummary] = useState<QuickSummaryResponse | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  const handleUploadSuccess = async (doc: {
    document_id: string;
    filename: string;
    status: string;
  }) => {
    setSuccessDocId(doc.document_id);
    setLoadingSummary(true);

    try {
      // Fast call for instant 2-3 sentence overview right after upload
      const summaryData = await apiClient.getQuickSummary(doc.document_id);
      setQuickSummary(summaryData);
    } catch (err) {
      console.error("Failed to generate quick summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="border-b border-[var(--border-subtle)] pb-6">
        <h1 className="font-serif text-2xl md:text-3xl font-bold text-[var(--accent-primary)]">
          Upload Contract Document
        </h1>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Select or drag a legal contract (NDA, Master Service Agreement, Employment Agreement, Policy) for fast first-pass overview and in-depth risk analysis.
        </p>
      </div>

      {/* Upload Dropzone Container */}
      <Card>
        <CardHeader>
          <CardTitle>File Ingestion &amp; Parsing Dropzone</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {successDocId ? (
            <div className="space-y-4">
              <div className="p-4 bg-[var(--risk-low-bg)] border border-[var(--risk-low)] text-[var(--risk-low)] text-xs flex items-center justify-between">
                <div>
                  <p className="font-bold font-serif text-sm">Upload Ingested Successfully</p>
                  <p className="text-[11px] mt-0.5">Asynchronous deep analysis pipeline running in background.</p>
                </div>
                <Link href={`/documents/${successDocId}`}>
                  <Button variant="primary" className="text-xs">
                    Open Full Review &rarr;
                  </Button>
                </Link>
              </div>

              {/* Instant Quick Summary Card */}
              {loadingSummary ? (
                <div className="p-5 border border-[var(--border-subtle)] bg-[var(--bg-page)] space-y-2 animate-pulse">
                  <div className="h-4 bg-[var(--border-subtle)] w-1/3 mb-2" />
                  <div className="h-3 bg-[var(--border-subtle)] w-full" />
                  <div className="h-3 bg-[var(--border-subtle)] w-5/6" />
                </div>
              ) : quickSummary ? (
                <div className="p-5 border border-[var(--border-subtle)] bg-[var(--bg-page)] space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-serif font-bold text-[var(--accent-primary)]">
                        {quickSummary.document_type}
                      </span>
                      <Badge variant={quickSummary.estimated_risk_level.toLowerCase() as any}>
                        {quickSummary.estimated_risk_level} Risk Initial Est.
                      </Badge>
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase">
                      Fast AI Overview
                    </span>
                  </div>

                  <p className="text-xs text-[var(--text-main)] leading-relaxed">
                    {quickSummary.quick_summary}
                  </p>

                  {quickSummary.key_points && quickSummary.key_points.length > 0 && (
                    <div className="pt-2 border-t border-[var(--border-subtle)] space-y-1">
                      <p className="text-[10px] uppercase font-semibold text-[var(--text-muted)] tracking-wider">
                        Initial Key Takeaways:
                      </p>
                      <ul className="text-xs text-[var(--text-main)] space-y-1 pl-4 list-disc">
                        {quickSummary.key_points.map((pt, idx) => (
                          <li key={idx}>{pt}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px] text-[var(--text-muted)]">
                    <span className="italic">{quickSummary.disclaimer}</span>
                    <Link href={`/documents/${successDocId}`}>
                      <Button variant="outline" className="text-xs py-1">
                        View Interactive Split-Pane Review &rarr;
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : null}
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
                OCR &amp; Text Extraction
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                Scanned documents automatically trigger Tesseract OCR fallback for text recovery.
              </p>
            </div>

            <div className="p-3 border border-[var(--border-subtle)] bg-[var(--bg-page)]">
              <h4 className="font-serif font-bold text-[var(--accent-primary)] mb-1">
                Instant Overview &amp; Full Analysis
              </h4>
              <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                A 2-3 sentence overview returns instantly, followed by comprehensive clause, risk, and compliance audit.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

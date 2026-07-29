"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ClauseHighlight } from "@/components/documents/clause-highlight";
import { Skeleton } from "@/components/ui/skeleton";

interface ClauseItem {
  type: string;
  text: string;
  risk_level?: string;
  explanation?: string;
}

interface CitationItem {
  source: string;
  citation: string;
}

interface DocumentDetail {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at?: string;
  analysis?: {
    summary?: string;
    safety_score?: number;
    risk_level?: string;
    clauses?: ClauseItem[];
    citations?: CitationItem[];
    compliance_checks?: Array<{
      rule_set: string;
      violations: string[];
    }>;
    extracted_text?: string;
  };
}

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const docId = resolvedParams.id;
  const router = useRouter();

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClauseText, setSelectedClauseText] = useState<string | null>(null);
  const [escalated, setEscalated] = useState(false);

  // Deletion state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDocument() {
      try {
        const data = await apiClient.getDocument(docId);
        setDocument(data);
        if (data.status === "escalated" || data.status === "flagged") {
          setEscalated(true);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load document analysis.");
      } finally {
        setLoading(false);
      }
    }
    loadDocument();
  }, [docId]);

  const handleEscalate = async () => {
    try {
      const res = await apiClient.escalateDocument(docId);
      if (res) {
        setEscalated(true);
        setDocument((prev) => (prev ? { ...prev, status: "escalated" } : prev));
      }
    } catch (e: any) {
      console.error("Failed to escalate document:", e);
      alert(e.message || "Failed to escalate document for human review.");
    }
  };

  const handleDeleteConfirm = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await apiClient.deleteDocument(docId);
      router.push("/dashboard");
    } catch (err: any) {
      console.error("Failed to delete document:", err);
      setDeleteError(err.message || "Failed to delete document. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header Skeleton */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <Skeleton className="h-7 w-64" />
              <Skeleton className="h-5 w-20" />
            </div>
            <Skeleton className="h-3 w-80" />
          </div>
          <div className="flex items-center space-x-3">
            <Skeleton className="h-9 w-40" />
            <Skeleton className="h-9 w-36" />
          </div>
        </div>

        {/* Split-Pane Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left Pane (Pane 1): 10 Skeleton Text Lines */}
          <Card className="h-[750px] flex flex-col">
            <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-28" />
            </CardHeader>
            <CardContent className="flex-1 p-4 space-y-4 bg-[var(--bg-page)] border-t border-[var(--border-subtle)] overflow-hidden">
              {[...Array(10)].map((_, i) => (
                <div key={i} className="flex items-center space-x-3">
                  <Skeleton className="h-3 w-6 shrink-0" />
                  <Skeleton className={`h-4 ${i % 3 === 0 ? "w-full" : i % 2 === 0 ? "w-5/6" : "w-3/4"}`} />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Right Pane (Pane 2): 3 Skeleton Clause Cards */}
          <div className="h-[750px] space-y-6">
            {/* Risk score summary card skeleton */}
            <Card>
              <CardHeader className="py-3 px-4">
                <Skeleton className="h-4 w-44" />
              </CardHeader>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-8 w-24" />
                </div>
                <div className="space-y-2">
                  <Skeleton className="h-3 w-28" />
                  <Skeleton className="h-4 w-48" />
                </div>
              </CardContent>
            </Card>

            {/* Identified Clauses List: 3 clause cards */}
            <Card>
              <CardHeader className="py-3 px-4">
                <Skeleton className="h-4 w-52" />
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                {[1, 2, 3].map((cardIdx) => (
                  <div key={cardIdx} className="space-y-2 border border-[var(--border-subtle)] p-3">
                    <div className="flex items-center justify-between">
                      <Skeleton className="h-4 w-36" />
                      <Skeleton className="h-5 w-16" />
                    </div>
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-3 w-3/4" />
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="p-8 max-w-xl mx-auto space-y-4">
        <div className="p-4 bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)] text-xs">
          {error || "Document not found."}
        </div>
        <Link href="/dashboard">
          <Button variant="secondary">Back to Dashboard</Button>
        </Link>
      </div>
    );
  }

  const analysis = document.analysis || {};
  const clauses = analysis.clauses || [];
  const citations = analysis.citations || [];
  const compliance = analysis.compliance_checks || [];
  const extractedText = analysis.extracted_text || "Extracted contract text unavailable.";
  const riskLevel = (analysis.risk_level?.toLowerCase() || "neutral") as "low" | "medium" | "high" | "neutral";

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="font-serif text-2xl font-bold text-[var(--accent-primary)]">
              {document.filename}
            </h1>
            <Badge variant={riskLevel}>{analysis.risk_level || "Neutral"} Risk</Badge>
            {escalated && (
              <Badge variant="high">Flagged for Human Review</Badge>
            )}
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Document ID: <span className="font-mono">{document.document_id}</span> | Status: <span className="uppercase font-semibold">{document.status}</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant={escalated ? "secondary" : "outline"}
            onClick={handleEscalate}
            disabled={escalated}
          >
            {escalated ? "Escalated for Partner Review" : "Escalate to Human Review"}
          </Button>
          <Link href={`/reports/${docId}`}>
            <Button variant="primary">Export Memo Report</Button>
          </Link>
          <Button
            variant="outline"
            className="border-[var(--risk-high)] text-[var(--risk-high)] hover:bg-[var(--risk-high-bg)]"
            onClick={() => setShowDeleteModal(true)}
          >
            Delete Document
          </Button>
        </div>
      </div>

      {/* Confirmation Dialog Overlay */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 no-print">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] p-6 max-w-md w-full rounded-none space-y-4">
            <h3 className="font-serif text-lg font-bold text-[var(--risk-high)]">
              Confirm Document Deletion
            </h3>
            <p className="text-xs text-[var(--text-main)] leading-relaxed">
              Permanently delete <strong className="font-semibold">{document.filename}</strong>? This will remove all analysis results, clauses, and audit records.
            </p>

            {deleteError && (
              <div className="p-3 text-xs bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)]">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end space-x-3 pt-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteError(null);
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="outline"
                className="border-[var(--risk-high)] text-white bg-[var(--risk-high)] hover:bg-red-700"
                onClick={handleDeleteConfirm}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Permanently Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Split-Pane Results View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Left Pane (Pane 1): Document Viewer / Original Text */}
        <Card className="h-[750px] flex flex-col">
          <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold">
              Pane 1: Extracted Document Text
            </CardTitle>
            <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-mono">
              OCR Parsing Verified
            </span>
          </CardHeader>
          <CardContent className="flex-1 p-4 overflow-y-auto font-mono text-xs leading-relaxed bg-[var(--bg-page)] space-y-2 border-t border-[var(--border-subtle)]">
            {extractedText.split("\n").map((line, idx) => {
              const isSelected = selectedClauseText && line.toLowerCase().includes(selectedClauseText.toLowerCase());
              return (
                <div
                  key={idx}
                  className={`flex items-start space-x-3 p-1 rounded-none transition-colors ${
                    isSelected
                      ? "bg-[var(--risk-medium-bg)] border-l-2 border-[var(--risk-medium)] font-semibold"
                      : "hover:bg-[var(--bg-surface)]"
                  }`}
                >
                  <span className="text-[10px] text-[var(--text-muted)] select-none w-8 text-right shrink-0">
                    {idx + 1}
                  </span>
                  <span className="flex-1 whitespace-pre-wrap select-text">
                    {line}
                  </span>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Right Pane (Pane 2): Identified Clauses & Risk Analysis */}
        <div className="h-[750px] overflow-y-auto space-y-6 pr-1">
          {/* Safety Score Card */}
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-semibold">
                Contract Risk Score Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-[var(--text-muted)]">Calculated Safety Metric</p>
                <p className="font-serif text-3xl font-bold text-[var(--accent-primary)] mt-1">
                  {analysis.safety_score !== undefined ? `${analysis.safety_score} / 100` : "N/A"}
                </p>
              </div>
              <div className="text-right max-w-xs">
                <p className="text-xs text-[var(--text-muted)] font-semibold uppercase tracking-wider">Executive Overview</p>
                <p className="text-xs text-[var(--text-main)] mt-1 leading-snug">
                  {analysis.summary || "Summary generation pending."}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Identified Clauses List */}
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm font-semibold">
                Identified Clauses & Risk Flags ({clauses.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {clauses.length === 0 ? (
                <p className="text-xs text-[var(--text-muted)]">No distinct clauses parsed yet.</p>
              ) : (
                clauses.map((c, i) => {
                  const level = (c.risk_level?.toLowerCase() || "low") as "low" | "medium" | "high";
                  return (
                    <div
                      key={i}
                      onClick={() => setSelectedClauseText(c.text)}
                      className="cursor-pointer"
                    >
                      <ClauseHighlight
                        title={c.type}
                        riskLevel={level}
                        text={c.text}
                      />
                      {c.explanation && (
                        <p className="text-[11px] text-[var(--text-muted)] mt-1.5 px-2 border-l-2 border-[var(--border-dark)]">
                          <strong>Risk Rationale:</strong> {c.explanation}
                        </p>
                      )}
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Standard Compliance Audit Results */}
          {compliance.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-sm font-semibold">
                  Standard NDA Compliance Audit
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-2">
                {compliance.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                      Rule Set: {item.rule_set}
                    </p>
                    {item.violations.length === 0 ? (
                      <p className="text-xs text-[var(--risk-low)] font-semibold">
                        ✓ Fully compliant with standard terms.
                      </p>
                    ) : (
                      item.violations.map((v, vIdx) => (
                        <div
                          key={vIdx}
                          className="p-2 text-xs bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)]"
                        >
                          ⚠ {v}
                        </div>
                      ))
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Precedent Citations */}
          {citations.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-sm font-semibold">
                  Legal Citations & Precedents
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {citations.map((cite, idx) => (
                  <div key={idx} className="border-b border-[var(--border-subtle)] pb-2 last:border-0">
                    <p className="text-xs font-bold text-[var(--accent-primary)]">{cite.source}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{cite.citation}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

interface ReportDetail {
  document_id: string;
  filename: string;
  summary: string;
  safety_score: number;
  risk_level: string;
  clauses: Array<{
    type: string;
    text: string;
    risk_level?: string;
    explanation?: string;
  }>;
  citations: Array<{
    source: string;
    citation: string;
  }>;
  compliance_checks?: Array<{
    rule_set: string;
    violations: string[];
  }>;
  generated_at?: string;
}

export default function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const docId = resolvedParams.id;

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadReport() {
      try {
        const data = await apiClient.getReport(docId);
        setReport(data);
      } catch (err: any) {
        setError(err.message || "Failed to load report.");
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [docId]);

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-[var(--text-muted)] animate-pulse">
        Generating print-ready memo report...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 max-w-xl mx-auto space-y-4">
        <div className="p-4 bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)] text-xs">
          {error || "Report not found."}
        </div>
        <Link href="/dashboard">
          <Button variant="secondary">Back to Dashboard</Button>
        </Link>
      </div>
    );
  }

  const currentDate = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const riskLevel = (report.risk_level?.toLowerCase() || "neutral") as "low" | "medium" | "high" | "neutral";

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Action Header - Hidden when printing */}
      <div className="no-print flex items-center justify-between border-b border-[var(--border-subtle)] pb-4">
        <Link href={`/documents/${docId}`}>
          <Button variant="secondary">← Back to Split-Pane</Button>
        </Link>
        <Button variant="primary" onClick={handlePrint}>
          Print / Save PDF Memo
        </Button>
      </div>

      {/* Print-Ready Legal Memorandum Container */}
      <div className="print-area bg-white p-8 md:p-12 border border-[var(--border-subtle)] text-[var(--text-main)] space-y-8">
        {/* Memo Header */}
        <div className="border-b-2 border-[var(--border-dark)] pb-6 space-y-4">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="font-serif text-3xl font-bold tracking-tight text-[var(--accent-primary)]">
                LEGAL AUDIT MEMORANDUM
              </h1>
              <p className="text-xs uppercase tracking-widest text-[var(--text-muted)] font-bold mt-1">
                FIRST-PASS CONTRACT REVIEW & RISK ASSESSMENT
              </p>
            </div>
            <div className="text-right">
              <Badge variant={riskLevel} className="text-xs px-3 py-1">
                {report.risk_level} RISK ASSIGNED
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs pt-4 border-t border-[var(--border-subtle)] font-mono">
            <div>
              <span className="text-[var(--text-muted)] block uppercase text-[10px]">DATE:</span>
              <span>{currentDate}</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block uppercase text-[10px]">DOCUMENT:</span>
              <span className="truncate block font-semibold">{report.filename}</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block uppercase text-[10px]">SAFETY SCORE:</span>
              <span className="font-bold text-sm">{report.safety_score} / 100</span>
            </div>
            <div>
              <span className="text-[var(--text-muted)] block uppercase text-[10px]">REFERENCE ID:</span>
              <span className="truncate block">{report.document_id}</span>
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <section className="space-y-3">
          <h2 className="font-serif text-lg font-bold text-[var(--accent-primary)] border-b border-[var(--border-subtle)] pb-1">
            1. Executive Summary
          </h2>
          <p className="text-xs leading-relaxed text-[var(--text-main)] bg-[var(--bg-page)] p-4 border border-[var(--border-subtle)]">
            {report.summary || "No executive summary available for this contract."}
          </p>
        </section>

        {/* Categorized Risk Matrix Table */}
        <section className="space-y-3">
          <h2 className="font-serif text-lg font-bold text-[var(--accent-primary)] border-b border-[var(--border-subtle)] pb-1">
            2. Categorized Clause & Risk Matrix
          </h2>
          {report.clauses.length === 0 ? (
            <p className="text-xs text-[var(--text-muted)]">No clauses identified.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/4">Clause Category</TableHead>
                  <TableHead className="w-1/6">Severity</TableHead>
                  <TableHead>Clause Content & Rationale</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.clauses.map((c, idx) => {
                  const level = (c.risk_level?.toLowerCase() || "low") as "low" | "medium" | "high" | "neutral";
                  return (
                    <TableRow key={idx}>
                      <TableCell className="font-serif font-bold text-xs">
                        {c.type}
                      </TableCell>
                      <TableCell>
                        <Badge variant={level}>{c.risk_level || "LOW"}</Badge>
                      </TableCell>
                      <TableCell className="space-y-1">
                        <p className="font-mono text-xs text-[var(--text-main)] bg-[var(--bg-page)] p-2 border border-[var(--border-subtle)]">
                          {c.text}
                        </p>
                        {c.explanation && (
                          <p className="text-[11px] text-[var(--text-muted)] italic">
                            Rationale: {c.explanation}
                          </p>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </section>

        {/* Legal Precedents & Citations */}
        {report.citations.length > 0 && (
          <section className="space-y-3">
            <h2 className="font-serif text-lg font-bold text-[var(--accent-primary)] border-b border-[var(--border-subtle)] pb-1">
              3. Statutory Precedents & Legal Authorities
            </h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-1/3">Authority / Source</TableHead>
                  <TableHead>Statutory Citation & Relevance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.citations.map((cite, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="font-bold text-xs text-[var(--accent-primary)]">
                      {cite.source}
                    </TableCell>
                    <TableCell className="text-xs text-[var(--text-main)]">
                      {cite.citation}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>
        )}

        {/* Memo Disclaimer Sign-off */}
        <section className="pt-6 border-t border-[var(--border-subtle)] text-[11px] text-[var(--text-muted)] space-y-1">
          <p>
            <strong>NOTICE:</strong> This memorandum is generated as an automated first-pass screening analysis.
            It does not constitute formal legal opinion or substitute for review by licensed legal counsel.
          </p>
        </section>
      </div>
    </div>
  );
}

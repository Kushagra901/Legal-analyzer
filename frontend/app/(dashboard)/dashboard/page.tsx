"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

interface DocumentItem {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at?: string | null;
  safety_score?: number | null;
  risk_level?: string | null;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search, Filter & Sort State Controls
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("NEWEST");

  useEffect(() => {
    async function loadDocuments() {
      try {
        const data = await apiClient.getDocuments();
        setDocuments(data.items || (Array.isArray(data) ? data : []));
      } catch (err: any) {
        setError(err.message || "Failed to load documents.");
      } finally {
        setLoading(false);
      }
    }
    loadDocuments();
  }, []);

  const totalDocs = documents.length;
  const highRiskCount = documents.filter((d) => d.risk_level === "HIGH").length;
  const processingCount = documents.filter((d) => d.status === "processing").length;
  const completedCount = documents.filter((d) => d.status === "completed").length;

  const filteredAndSortedDocuments = documents
    .filter((doc) => {
      // Search term filter
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        if (!doc.filename.toLowerCase().includes(query)) {
          return false;
        }
      }
      // Status filter
      if (statusFilter !== "ALL") {
        if (doc.status.toUpperCase() !== statusFilter) {
          return false;
        }
      }
      // Risk level filter
      if (riskFilter !== "ALL") {
        const docRisk = (doc.risk_level || "").toUpperCase();
        if (docRisk !== riskFilter) {
          return false;
        }
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === "NEWEST") {
        const dateA = a.uploaded_at ? new Date(a.uploaded_at).getTime() : 0;
        const dateB = b.uploaded_at ? new Date(b.uploaded_at).getTime() : 0;
        return dateB - dateA;
      }
      if (sortBy === "OLDEST") {
        const dateA = a.uploaded_at ? new Date(a.uploaded_at).getTime() : 0;
        const dateB = b.uploaded_at ? new Date(b.uploaded_at).getTime() : 0;
        return dateA - dateB;
      }
      if (sortBy === "HIGHEST_RISK") {
        const riskRank: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
        const rankA = riskRank[(a.risk_level || "").toUpperCase()] || 0;
        const rankB = riskRank[(b.risk_level || "").toUpperCase()] || 0;
        if (rankA !== rankB) return rankB - rankA;
        const scoreA = a.safety_score ?? 100;
        const scoreB = b.safety_score ?? 100;
        return scoreA - scoreB;
      }
      if (sortBy === "LOWEST_RISK") {
        const riskRank: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
        const rankA = riskRank[(a.risk_level || "").toUpperCase()] || 0;
        const rankB = riskRank[(b.risk_level || "").toUpperCase()] || 0;
        if (rankA !== rankB) return rankA - rankB;
        const scoreA = a.safety_score ?? 100;
        const scoreB = b.safety_score ?? 100;
        return scoreB - scoreA;
      }
      return 0;
    });

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
        <div>
          <h1 className="font-serif text-2xl md:text-3xl font-bold text-[var(--accent-primary)]">
            Contract Workspace & Document Overview
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Central repository for contract extractions, risk scoring, and compliance audits.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link href="/documents/upload">
            <Button variant="primary">Upload Document</Button>
          </Link>
          <Link href="/review">
            <Button variant="outline">Clause Review Queue</Button>
          </Link>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {loading ? (
          [1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-2">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-7 w-12" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Total Documents
                </p>
                <p className="font-serif text-2xl font-bold text-[var(--accent-primary)] mt-1">
                  {totalDocs}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  High Risk Flagged
                </p>
                <p className="font-serif text-2xl font-bold text-[var(--risk-high)] mt-1">
                  {highRiskCount}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Completed Audits
                </p>
                <p className="font-serif text-2xl font-bold text-[var(--risk-low)] mt-1">
                  {completedCount}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Processing Queue
                </p>
                <p className="font-serif text-2xl font-bold text-[var(--accent-primary)] mt-1">
                  {processingCount}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Search, Filter & Sort Controls */}
      <Card className="p-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search Input */}
          <div className="flex-1 min-w-[240px]">
            <label className="block text-[10px] uppercase font-semibold text-[var(--text-muted)] tracking-wider mb-1">
              Search Filename
            </label>
            <input
              type="text"
              placeholder="Search contract name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full text-xs border border-[var(--border-subtle)] px-3 py-1.5 bg-white text-[var(--text-main)] focus:outline-none focus:border-[var(--accent-primary)] rounded-none"
            />
          </div>

          {/* Sort Dropdown */}
          <div className="w-full md:w-56">
            <label className="block text-[10px] uppercase font-semibold text-[var(--text-muted)] tracking-wider mb-1">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full text-xs border border-[var(--border-subtle)] px-3 py-1.5 bg-white text-[var(--text-main)] focus:outline-none focus:border-[var(--accent-primary)] cursor-pointer rounded-none"
            >
              <option value="NEWEST">Newest First</option>
              <option value="OLDEST">Oldest First</option>
              <option value="HIGHEST_RISK">Highest Risk</option>
              <option value="LOWEST_RISK">Lowest Risk</option>
            </select>
          </div>
        </div>

        {/* Filter Buttons */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-3 border-t border-[var(--border-subtle)]">
          {/* Status Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] uppercase font-semibold text-[var(--text-muted)] tracking-wider mr-1">
              Status:
            </span>
            {["ALL", "COMPLETED", "PROCESSING", "FAILED"].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-2.5 py-1 text-[10px] font-semibold border transition-colors cursor-pointer rounded-none ${
                  statusFilter === status
                    ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)]"
                    : "bg-white text-[var(--text-main)] border-[var(--border-subtle)] hover:bg-[var(--bg-page)]"
                }`}
              >
                {status}
              </button>
            ))}
          </div>

          {/* Risk Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] uppercase font-semibold text-[var(--text-muted)] tracking-wider mr-1">
              Risk Level:
            </span>
            {["ALL", "HIGH", "MEDIUM", "LOW"].map((level) => (
              <button
                key={level}
                onClick={() => setRiskFilter(level)}
                className={`px-2.5 py-1 text-[10px] font-semibold border transition-colors cursor-pointer rounded-none ${
                  riskFilter === level
                    ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)]"
                    : "bg-white text-[var(--text-main)] border-[var(--border-subtle)] hover:bg-[var(--bg-page)]"
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Document List Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Contract Extractions ({filteredAndSortedDocuments.length})</CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              Click any document to inspect the interactive split-pane results or view the formal memo report.
            </p>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {error ? (
            <div className="p-6 text-xs text-[var(--risk-high)] bg-[var(--risk-high-bg)]">
              {error}
            </div>
          ) : loading ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document Filename</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Safety Score</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Uploaded Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[1, 2, 3].map((rowIdx) => (
                  <TableRow key={rowIdx}>
                    <TableCell><Skeleton className="h-4 w-44" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end space-x-2">
                        <Skeleton className="h-7 w-28" />
                        <Skeleton className="h-7 w-24" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : documents.length === 0 ? (
            <div className="p-8">
              <EmptyState
                title="No Contract Documents Uploaded Yet"
                description="Upload a contract (PDF, DOCX, TXT) to perform automated OCR, clause identification, and risk scoring."
                actionLabel="Upload First Contract"
                onAction={() => (window.location.href = "/documents/upload")}
              />
            </div>
          ) : filteredAndSortedDocuments.length === 0 ? (
            <div className="p-8">
              <EmptyState
                title="No Matching Contract Documents"
                description="No contract extractions match the selected search query, status, or risk filters."
                actionLabel="Clear Filters"
                onAction={() => {
                  setSearchTerm("");
                  setStatusFilter("ALL");
                  setRiskFilter("ALL");
                  setSortBy("NEWEST");
                }}
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Document Filename</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Safety Score</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Uploaded Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAndSortedDocuments.map((doc) => {
                  const level = (doc.risk_level?.toLowerCase() || "neutral") as "low" | "medium" | "high" | "neutral";
                  const formattedDate = doc.uploaded_at
                    ? new Date(doc.uploaded_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })
                    : "—";

                  return (
                    <TableRow key={doc.document_id}>
                      <TableCell className="font-semibold font-serif text-sm">
                        <Link
                          href={`/documents/${doc.document_id}`}
                          className="hover:underline text-[var(--accent-primary)]"
                        >
                          {doc.filename}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={doc.status === "completed" ? "low" : "neutral"}>
                          {doc.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {doc.safety_score !== undefined && doc.safety_score !== null
                          ? `${doc.safety_score} / 100`
                          : "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={level}>
                          {doc.risk_level || "Pending"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-[var(--text-muted)]">
                        {formattedDate}
                      </TableCell>
                      <TableCell className="text-right space-x-2">
                        <Link href={`/documents/${doc.document_id}`}>
                          <Button variant="secondary" className="text-[10px] py-1 px-2">
                            Inspect Split-Pane
                          </Button>
                        </Link>
                        <Link href={`/reports/${doc.document_id}`}>
                          <Button variant="outline" className="text-[10px] py-1 px-2">
                            Memo Report
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

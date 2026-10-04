"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

interface FlaggedClauseItem {
  clause_id?: string;
  document_id: string;
  document_filename: string;
  type: string;
  text: string;
  risk_level: "low" | "medium" | "high";
  explanation?: string;
  status: "pending" | "approved" | "redline_flagged";
  note?: string;
}

export default function ReviewQueuePage() {
  const [items, setItems] = useState<FlaggedClauseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [userNotes, setUserNotes] = useState<Record<number, string>>({});
  const [notification, setNotification] = useState<string | null>(null);
  const [submittingIndex, setSubmittingIndex] = useState<number | null>(null);

  useEffect(() => {
    async function loadReviewQueue() {
      try {
        const response = await apiClient.getDocuments();
        const docs = response.items || (Array.isArray(response) ? response : []);
        const queue: FlaggedClauseItem[] = [];

        // Fetch detail and reviews for each document to populate review queue
        for (const doc of docs) {
          try {
            const [detail, reviews] = await Promise.all([
              apiClient.getDocument(doc.document_id),
              apiClient.getDocumentReviews(doc.document_id).catch(() => []),
            ]);

            const reviewsMap: Record<string, { decision: string; note?: string | null }> = {};
            for (const r of reviews) {
              reviewsMap[r.clause_id] = { decision: r.decision, note: r.note };
            }

            const clauses = detail.analysis?.clauses || [];
            for (const c of clauses) {
              const rev = c.id ? reviewsMap[c.id] : undefined;
              const statusVal = (rev?.decision as "pending" | "approved" | "redline_flagged") || "pending";

              queue.push({
                clause_id: c.id,
                document_id: doc.document_id,
                document_filename: doc.filename,
                type: c.type,
                text: c.text,
                risk_level: (c.severity?.toLowerCase() || c.risk_level?.toLowerCase() || "low") as "low" | "medium" | "high",
                explanation: c.explanation,
                status: statusVal,
                note: rev?.note || "",
              });
            }
          } catch (e) {
            console.error(`Failed to fetch detail/reviews for ${doc.document_id}:`, e);
          }
        }
        setItems(queue);
      } catch (err) {
        console.error("Failed to load review queue:", err);
      } finally {
        setLoading(false);
      }
    }
    loadReviewQueue();
  }, []);

  const handleAction = async (index: number, newStatus: "approved" | "redline_flagged") => {
    const item = items[index];
    if (!item.clause_id) {
      console.error("Missing clause_id for review item");
      return;
    }

    setSubmittingIndex(index);
    const noteToSubmit = userNotes[index] !== undefined ? userNotes[index] : item.note || "";

    try {
      await apiClient.createOrUpdateClauseReview(item.document_id, item.clause_id, {
        decision: newStatus,
        note: noteToSubmit,
      });

      setItems((prev) =>
        prev.map((it, idx) =>
          idx === index
            ? { ...it, status: newStatus, note: noteToSubmit }
            : it
        )
      );

      const actionText = newStatus === "approved" ? "approved" : "flagged for redlining";
      setNotification(`Clause "${item.type}" in ${item.document_filename} was successfully ${actionText}.`);

      setTimeout(() => {
        setNotification(null);
      }, 5000);
    } catch (err: any) {
      console.error("Failed to persist review action:", err);
      alert(err.message || "Failed to persist clause review decision.");
    } finally {
      setSubmittingIndex(null);
    }
  };

  const filteredItems = items.filter((item) => {
    if (filterSeverity === "ALL") return true;
    return item.risk_level.toUpperCase() === filterSeverity;
  });

  const pendingCount = items.filter((i) => i.status === "pending").length;
  const approvedCount = items.filter((i) => i.status === "approved").length;
  const redlineCount = items.filter((i) => i.status === "redline_flagged").length;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
        <div>
          <h1 className="font-serif text-2xl md:text-3xl font-bold text-[var(--accent-primary)]">
            Attorney Clause Review Queue
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Iterate through parsed contract clauses across all documents, sign off on acceptable terms, or flag clauses for redlining.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="p-2 bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)] font-bold">
            Redline Flagged: {redlineCount}
          </span>
          <span className="p-2 bg-[var(--risk-low-bg)] border border-[var(--risk-low)] text-[var(--risk-low)] font-bold">
            Approved: {approvedCount}
          </span>
          <span className="p-2 bg-[var(--bg-page)] border border-[var(--border-subtle)] text-[var(--text-muted)] font-bold">
            Pending: {pendingCount}
          </span>
        </div>
      </div>

      {/* Action Notification Confirmation Banner */}
      {notification && (
        <div className="p-4 border border-[var(--risk-low)] bg-[var(--risk-low-bg)] text-[var(--risk-low)] text-xs font-semibold flex items-center justify-between">
          <span>{notification}</span>
          <button
            onClick={() => setNotification(null)}
            className="font-bold underline cursor-pointer text-xs ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Severity Filter Controls */}
      <div className="flex items-center space-x-3 text-xs font-semibold">
        <span className="text-[var(--text-muted)] uppercase tracking-wider text-[10px]">Filter Severity:</span>
        {["ALL", "HIGH", "MEDIUM", "LOW"].map((level) => (
          <button
            key={level}
            onClick={() => setFilterSeverity(level)}
            className={`px-3 py-1 border transition-colors cursor-pointer ${
              filterSeverity === level
                ? "bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] font-bold"
                : "bg-white text-[var(--text-main)] border-[var(--border-subtle)] hover:bg-[var(--bg-page)]"
            }`}
          >
            {level}
          </button>
        ))}
      </div>

      {/* Queue List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-48" />
                </div>
                <Skeleton className="h-5 w-24" />
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-3 w-3/4" />
                <div className="pt-2 flex items-center justify-between gap-3 border-t border-[var(--border-subtle)]">
                  <Skeleton className="h-7 flex-1" />
                  <div className="flex items-center space-x-2 shrink-0">
                    <Skeleton className="h-7 w-24" />
                    <Skeleton className="h-7 w-28" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No Flagged Clauses Found"
          description={
            filterSeverity === "ALL"
              ? "All contract documents have been reviewed or no risk clauses were detected."
              : `No clauses found matching severity filter: ${filterSeverity}.`
          }
        />
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item, idx) => (
            <Card key={idx} className={item.status === "approved" ? "opacity-60 bg-[var(--bg-page)]" : ""}>
              <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Badge variant={item.risk_level}>{item.risk_level} RISK</Badge>
                  <span className="font-serif font-bold text-sm text-[var(--accent-primary)]">
                    {item.type}
                  </span>
                  <span className="text-xs text-[var(--text-muted)] border-l border-[var(--border-subtle)] pl-3">
                    Contract:{" "}
                    <Link
                      href={`/documents/${item.document_id}`}
                      className="hover:underline font-semibold text-[var(--accent-primary)]"
                    >
                      {item.document_filename}
                    </Link>
                  </span>
                </div>
                <div>
                  {item.status === "approved" && (
                    <Badge variant="low">Approved</Badge>
                  )}
                  {item.status === "redline_flagged" && (
                    <Badge variant="high">Flagged for Redline</Badge>
                  )}
                  {item.status === "pending" && (
                    <Badge variant="neutral">Pending Sign-off</Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                <p className="font-mono text-xs text-[var(--text-main)] bg-[var(--bg-page)] p-3 border border-[var(--border-subtle)] leading-relaxed">
                  {item.text}
                </p>
                {item.explanation && (
                  <p className="text-[11px] text-[var(--text-muted)] border-l-2 border-[var(--accent-primary)] pl-2">
                    <strong>System Assessment:</strong> {item.explanation}
                  </p>
                )}

                {/* Reviewer Note Input & Action Buttons */}
                <div className="pt-2 flex flex-col md:flex-row md:items-center justify-between gap-3 border-t border-[var(--border-subtle)]">
                  <input
                    type="text"
                    placeholder="Add optional attorney review note..."
                    value={userNotes[idx] !== undefined ? userNotes[idx] : item.note || ""}
                    onChange={(e) =>
                      setUserNotes({ ...userNotes, [idx]: e.target.value })
                    }
                    className="text-xs border border-[var(--border-subtle)] px-3 py-1.5 flex-1 bg-white focus:outline-none focus:border-[var(--accent-primary)]"
                  />
                  <div className="flex items-center space-x-2 shrink-0">
                    <Button
                      variant="secondary"
                      className="text-[10px] py-1"
                      disabled={submittingIndex === idx}
                      onClick={() => handleAction(idx, "approved")}
                    >
                      {submittingIndex === idx ? "Saving..." : "Approve Term"}
                    </Button>
                    <Button
                      variant="outline"
                      className="text-[10px] py-1 border-[var(--risk-high)] text-[var(--risk-high)] hover:bg-[var(--risk-high-bg)]"
                      disabled={submittingIndex === idx}
                      onClick={() => handleAction(idx, "redline_flagged")}
                    >
                      {submittingIndex === idx ? "Saving..." : "Flag for Redline"}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

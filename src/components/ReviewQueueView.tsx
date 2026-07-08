/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ArrowLeft, Check, AlertTriangle, FileText, ChevronRight, CheckCircle, ShieldAlert, BookOpen } from 'lucide-react';
import { LegalDocument, ExtractedClause } from '../types';

interface ReviewQueueViewProps {
  documents: LegalDocument[];
  onBackToDashboard: () => void;
  onSelectDocument: (doc: LegalDocument) => void;
  onUpdateClause: (docId: string, clauseId: string, updates: Partial<ExtractedClause>) => void;
}

export default function ReviewQueueView({
  documents,
  onBackToDashboard,
  onSelectDocument,
  onUpdateClause
}: ReviewQueueViewProps) {
  // Filter for flagged documents first or those with un-reviewed high-risk items
  const flaggedDocs = documents.filter(d => d.status === 'flagged' || d.clauses.some(c => c.flaggedForReview && !c.humanReviewed));
  const [selectedDocId, setSelectedDocId] = useState<string | null>(flaggedDocs[0]?.id || null);

  const selectedDoc = documents.find(d => d.id === selectedDocId);
  const flaggedClauses = selectedDoc ? selectedDoc.clauses.filter(c => c.flaggedForReview && !c.humanReviewed) : [];
  const reviewedClauses = selectedDoc ? selectedDoc.clauses.filter(c => c.humanReviewed || !c.flaggedForReview) : [];

  const handleVerifyClause = (clauseId: string) => {
    if (selectedDocId) {
      onUpdateClause(selectedDocId, clauseId, {
        humanReviewed: true,
        flaggedForReview: false
      });
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 text-left" id="review-queue-container">
      {/* Top Navigation */}
      <button
        id="review-back-btn"
        onClick={onBackToDashboard}
        className="flex items-center space-x-1.5 text-xs text-ink-muted font-mono uppercase tracking-wider hover:text-ink-dark transition-colors mb-6 cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Dashboard</span>
      </button>

      <div className="mb-8" id="review-intro">
        <div className="flex items-center space-x-2 text-risk-medium font-mono text-xs uppercase tracking-wider mb-1">
          <BookOpen className="w-4 h-4" />
          <span>Sovereign Review Officer Desk</span>
        </div>
        <h1 className="font-serif text-3xl font-medium tracking-tight text-ink-dark mb-2">
          Human Review & Verification Queue
        </h1>
        <p className="text-ink-muted text-sm leading-relaxed max-w-2xl">
          Supervise automated legal assessments. Confirm flags, override confidence scores, correct machine-extracted clauses, and approve drafts before formal corporate sign-off.
        </p>
      </div>

      {flaggedDocs.length === 0 ? (
        <div className="border border-border-subtle bg-bg-card p-12 text-center" id="empty-queue-block">
          <CheckCircle className="w-10 h-10 text-risk-low mx-auto mb-3 stroke-1" />
          <h3 className="font-serif text-xl font-medium text-ink-dark mb-1">Queue Fully Cleared</h3>
          <p className="text-ink-muted text-xs font-sans max-w-md mx-auto">
            All uploaded legal contracts have been human-audited or are verified low-exposure drafts. No documents are currently awaiting manual exception review.
          </p>
          <button
            id="queue-dashboard-btn"
            onClick={onBackToDashboard}
            className="mt-4 border border-accent-forest hover:bg-accent-forest-light text-accent-forest text-xs font-mono uppercase tracking-wider px-4 py-2 transition-colors cursor-pointer"
          >
            Go to Document Repository
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8" id="review-queue-layout">
          {/* Left Column: Flagged Documents List (Serious Table Sidebar) */}
          <div className="lg:col-span-4 space-y-3" id="flagged-docs-sidebar">
            <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-bold block mb-1">
              Flagged Contracts ({flaggedDocs.length})
            </span>

            <div className="divide-y divide-border-subtle border border-border-subtle" id="flagged-docs-list">
              {flaggedDocs.map((doc) => {
                const isSelected = doc.id === selectedDocId;
                const outstandingFlags = doc.clauses.filter(c => c.flaggedForReview && !c.humanReviewed).length;

                return (
                  <div
                    key={doc.id}
                    id={`review-doc-card-${doc.id}`}
                    onClick={() => setSelectedDocId(doc.id)}
                    className={`p-4 cursor-pointer text-left transition-all relative ${
                      isSelected
                        ? 'bg-accent-forest-light/60 border-l-4 border-l-accent-forest'
                        : 'bg-transparent hover:bg-bg-card'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-[10px] font-mono text-ink-muted">{doc.uploadDate}</span>
                      <span className="text-[10px] font-mono text-risk-high bg-risk-high-bg border border-risk-high/20 px-1.5 py-0.2">
                        {outstandingFlags} pending flags
                      </span>
                    </div>
                    <h4 className="font-serif text-sm font-semibold text-ink-dark mt-1.5 leading-snug group-hover:text-accent-forest transition-colors">
                      {doc.name}
                    </h4>
                    <div className="flex items-center justify-between text-xs font-mono text-ink-muted mt-2">
                      <span>Index: {doc.complianceScore}%</span>
                      <span className="text-accent-forest font-semibold hover:underline flex items-center" onClick={(e) => {
                        e.stopPropagation();
                        onSelectDocument(doc);
                      }}>
                        Workspace <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active Document Auditing Details */}
          <div className="lg:col-span-8 space-y-6" id="active-review-pane">
            {selectedDoc ? (
              <div className="border border-border-subtle p-6 bg-transparent" id="active-document-auditor-panel">
                <div className="border-b border-border-subtle pb-4 mb-4 text-left" id="active-review-header">
                  <span className="text-xs font-mono uppercase tracking-wider text-accent-forest font-semibold">Currently Auditing:</span>
                  <h3 className="font-serif text-xl font-bold text-ink-dark mt-0.5">{selectedDoc.name}</h3>
                  <div className="flex items-center space-x-4 text-xs font-mono text-ink-muted mt-2">
                    <span>Audit Confidence: {selectedDoc.reviewConfidence}%</span>
                    <span>•</span>
                    <span>Original Size: {selectedDoc.fileSize}</span>
                    <span>•</span>
                    <span>Total Clauses: {selectedDoc.clauses.length}</span>
                  </div>
                </div>

                {/* Sub-section: Pending Exception Flags */}
                <div className="space-y-4" id="pending-exceptions-list">
                  <div className="flex items-center justify-between" id="exceptions-header">
                    <span className="text-xs font-mono uppercase tracking-wider text-risk-high font-bold flex items-center space-x-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Pending Exception Flags ({flaggedClauses.length})</span>
                    </span>
                    <span className="text-[10px] text-ink-muted font-mono">Verify to resolve document blockages</span>
                  </div>

                  {flaggedClauses.length === 0 ? (
                    <div className="p-8 bg-risk-low-bg/20 border border-risk-low/25 text-center" id="exceptions-cleared">
                      <CheckCircle className="w-8 h-8 text-risk-low mx-auto mb-2" />
                      <span className="block font-serif text-sm font-semibold text-ink-dark">All Critical Flags Resolved</span>
                      <span className="text-xs text-ink-muted font-sans mt-0.5 block">
                        This contract's critical risk alerts have been resolved. Approve document status to complete audit.
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-4" id="flagged-clauses-container">
                      {flaggedClauses.map((clause) => {
                        return (
                          <div
                            key={clause.id}
                            id={`exception-clause-card-${clause.id}`}
                            className="border border-risk-high/20 bg-[#fcfcfc] p-5 text-left relative"
                          >
                            <div className="flex items-start justify-between gap-4 border-b border-border-subtle/50 pb-2 mb-3">
                              <div>
                                <span className="font-serif text-sm font-bold text-ink-dark block">
                                  {clause.title}
                                </span>
                                <span className="text-[10px] font-mono uppercase text-ink-muted">
                                  Category: {clause.category}
                                </span>
                              </div>
                              <span className="px-2 py-0.5 text-[10px] font-mono uppercase font-semibold text-risk-high bg-risk-high-bg border border-risk-high/30">
                                {clause.riskLevel} risk
                              </span>
                            </div>

                            <div className="space-y-3 text-xs text-ink-dark/90 font-sans" id={`exception-clause-body-${clause.id}`}>
                              <div className="bg-bg-card p-3 border-l-2 border-border-subtle font-serif italic text-ink-muted">
                                "{clause.text}"
                              </div>
                              <p className="leading-relaxed">
                                <strong className="font-mono text-[9px] tracking-wider text-ink-muted uppercase block">AI Analysis Exception:</strong>
                                {clause.explanation}
                              </p>
                              <p className="leading-relaxed bg-accent-forest-light/40 p-2.5 border border-accent-forest/10">
                                <strong className="font-mono text-[9px] tracking-wider text-accent-forest uppercase block">Drafter counter-revision:</strong>
                                {clause.suggestedAction}
                              </p>
                            </div>

                            <div className="flex justify-end pt-4 mt-3 border-t border-border-subtle/40" id={`exception-clause-actions-${clause.id}`}>
                              <button
                                id={`verify-clause-btn-${clause.id}`}
                                onClick={() => handleVerifyClause(clause.id)}
                                className="bg-accent-forest hover:bg-opacity-90 text-white font-mono text-[10px] uppercase tracking-wider px-3.5 py-1.5 flex items-center space-x-1.5 transition-colors cursor-pointer"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>Verify and Clear Flag</span>
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Sub-section: Already Approved/Symmetrical clauses */}
                {reviewedClauses.length > 0 && (
                  <div className="mt-8 pt-6 border-t border-border-subtle text-left" id="approved-clauses-wrapper">
                    <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-bold block mb-3">
                      Approved or Low-Risk Clauses ({reviewedClauses.length})
                    </span>
                    <div className="space-y-2 max-h-[250px] overflow-y-auto pr-1" id="approved-clauses-list">
                      {reviewedClauses.map((c) => {
                        return (
                          <div key={c.id} id={`approved-clause-${c.id}`} className="border border-border-subtle/60 p-3 bg-bg-card/30 flex items-center justify-between text-xs font-sans">
                            <div className="text-left">
                              <span className="font-serif font-semibold text-ink-dark block">{c.title}</span>
                              <span className="text-[10px] font-mono text-ink-muted">Category: {c.category}</span>
                            </div>
                            <div className="flex items-center space-x-2 text-risk-low font-mono text-[10px] uppercase">
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span>Verified Symmetrical</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="border border-border-subtle p-12 text-center text-ink-muted" id="select-doc-reminder">
                Select a contract from the review queue sidebar to oversee compliance exceptions.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

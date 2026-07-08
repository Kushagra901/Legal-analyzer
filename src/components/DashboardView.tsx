/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Search, Filter, Plus, FileText, AlertTriangle, CheckCircle, ShieldAlert, LogOut, ArrowRight, BookOpen } from 'lucide-react';
import { LegalDocument, RiskLevel, DocumentStatus, UserSession } from '../types';

interface DashboardViewProps {
  documents: LegalDocument[];
  onSelectDocument: (doc: LegalDocument) => void;
  onNavigateToUpload: () => void;
  onNavigateToReviewQueue: () => void;
  onLogout: () => void;
  user: UserSession;
  onDeleteDocument: (id: string) => void;
}

export default function DashboardView({
  documents,
  onSelectDocument,
  onNavigateToUpload,
  onNavigateToReviewQueue,
  onLogout,
  user,
  onDeleteDocument
}: DashboardViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<RiskLevel | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'score' | 'name'>('date');

  // Filter documents
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          doc.summary.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRisk = riskFilter === 'all' ? true : doc.riskLevel === riskFilter;
    const matchesStatus = statusFilter === 'all' ? true : doc.status === statusFilter;
    return matchesSearch && matchesRisk && matchesStatus;
  });

  // Sort documents
  const sortedDocs = [...filteredDocs].sort((a, b) => {
    if (sortBy === 'date') {
      return new Date(b.uploadDate).getTime() - new Date(a.uploadDate).getTime();
    } else if (sortBy === 'score') {
      return b.complianceScore - a.complianceScore;
    } else {
      return a.name.localeCompare(b.name);
    }
  });

  // Count metrics for quiet metadata display
  const highRiskCount = documents.filter(d => d.riskLevel === 'high').length;
  const flaggedCount = documents.filter(d => d.status === 'flagged').length;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8" id="dashboard-container">
      {/* Editorial Profile Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-border-subtle pb-6 mb-8" id="dashboard-header">
        <div id="header-profile-info">
          <div className="flex items-center space-x-2 text-xs text-accent-forest font-mono tracking-wider uppercase mb-1">
            <span>Secure System Access</span>
            <span className="w-1.5 h-1.5 bg-accent-forest rounded-full"></span>
          </div>
          <h2 className="font-serif text-2xl font-medium text-ink-dark">
            Workspace: {user.name}
          </h2>
          <p className="text-ink-muted text-xs font-mono mt-0.5">
            {user.role} • {user.email}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-4 md:mt-0" id="header-actions">
          <button
            id="review-queue-btn"
            onClick={onNavigateToReviewQueue}
            className="border border-border-subtle hover:bg-accent-forest-light text-ink-dark px-4 py-2 text-xs font-mono tracking-wider uppercase transition-colors cursor-pointer flex items-center space-x-1.5"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Human Review Queue ({flaggedCount})</span>
          </button>

          <button
            id="new-document-btn"
            onClick={onNavigateToUpload}
            className="bg-accent-forest hover:bg-opacity-90 text-white px-4 py-2 text-xs font-mono tracking-wider uppercase transition-all cursor-pointer flex items-center space-x-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Analyze Document</span>
          </button>

          <button
            id="logout-btn"
            onClick={onLogout}
            title="Disconnect session"
            className="p-2 border border-border-subtle hover:bg-red-50 text-ink-muted hover:text-red-700 transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Overview Analytics Bar - Subtle & Integrated, Not Boxes */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 border-b border-border-subtle pb-8 mb-8 text-left" id="dashboard-metrics-summary">
        <div>
          <span className="block text-xs font-mono uppercase tracking-wider text-ink-muted">Total Agreements Audited</span>
          <span className="font-serif text-3xl font-light text-ink-dark mt-1 block">{documents.length}</span>
          <span className="text-xs text-ink-muted font-mono mt-1 block">Contract repository active</span>
        </div>
        <div>
          <span className="block text-xs font-mono uppercase tracking-wider text-ink-muted">Awaiting Human Auditing</span>
          <span className="font-serif text-3xl font-light text-risk-high mt-1 block">{flaggedCount}</span>
          <span className="text-xs text-ink-muted font-mono mt-1 block">Clauses requiring attention</span>
        </div>
        <div>
          <span className="block text-xs font-mono uppercase tracking-wider text-ink-muted">Severe Risk Exposure</span>
          <span className="font-serif text-3xl font-light text-risk-medium mt-1 block">{highRiskCount}</span>
          <span className="text-xs text-ink-muted font-mono mt-1 block">Critical breaches identified</span>
        </div>
      </div>

      {/* Filter and Search Bar controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6" id="dashboard-controls">
        <div className="relative flex-1" id="search-input-wrapper">
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-ink-muted" />
          <input
            id="dashboard-search"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search files by name, summary, or extracted clause context..."
            className="w-full bg-transparent border border-border-subtle pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-accent-forest rounded-none transition-colors font-sans"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs font-mono" id="filter-options">
          <div className="flex items-center space-x-1.5 border border-border-subtle px-3 py-2 bg-transparent" id="filter-risk-wrapper">
            <Filter className="w-3 h-3 text-ink-muted" />
            <span className="text-ink-muted uppercase">Risk:</span>
            <select
              id="risk-select-filter"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value as RiskLevel | 'all')}
              className="bg-transparent focus:outline-none text-ink-dark cursor-pointer font-semibold"
            >
              <option value="all">ALL LEVELS</option>
              <option value="low">LOW RISK</option>
              <option value="medium">MEDIUM RISK</option>
              <option value="high">HIGH RISK</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5 border border-border-subtle px-3 py-2 bg-transparent" id="filter-status-wrapper">
            <span className="text-ink-muted uppercase">Status:</span>
            <select
              id="status-select-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as DocumentStatus | 'all')}
              className="bg-transparent focus:outline-none text-ink-dark cursor-pointer font-semibold"
            >
              <option value="all">ALL STATUSES</option>
              <option value="completed">COMPLETED</option>
              <option value="flagged">FLAGGED REVIEW</option>
              <option value="processing">PROCESSING</option>
              <option value="failed">FAILED</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5 border border-border-subtle px-3 py-2 bg-transparent" id="sort-by-wrapper">
            <span className="text-ink-muted uppercase">Sort:</span>
            <select
              id="sort-select-filter"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'date' | 'score' | 'name')}
              className="bg-transparent focus:outline-none text-ink-dark cursor-pointer font-semibold"
            >
              <option value="date">DATE UPLOADED</option>
              <option value="score">COMPLIANCE INDEX</option>
              <option value="name">ALPHABETICAL</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Document Table */}
      <div className="border border-border-subtle overflow-x-auto bg-transparent" id="document-table-container">
        {sortedDocs.length === 0 ? (
          <div className="py-16 text-center border-t border-border-subtle" id="empty-table-state">
            <FileText className="w-8 h-8 text-ink-muted/50 mx-auto mb-3 stroke-1" />
            <h4 className="font-serif text-lg text-ink-dark mb-1">No Agreements Found</h4>
            <p className="text-ink-muted text-xs font-sans max-w-sm mx-auto">
              No legal documents match your filters or search terms. Try revising query parameters or upload a new contract for analysis.
            </p>
            <button
              id="empty-state-upload-btn"
              onClick={onNavigateToUpload}
              className="mt-4 border border-accent-forest hover:bg-accent-forest-light text-accent-forest text-xs font-mono uppercase tracking-wider px-4 py-2 transition-colors cursor-pointer"
            >
              Upload Document
            </button>
          </div>
        ) : (
          <table className="w-full text-left border-collapse" id="document-table">
            <thead>
              <tr className="bg-bg-card border-b border-border-subtle text-xs font-mono uppercase tracking-wider text-ink-muted">
                <th className="py-3 px-4 font-medium">Document Name</th>
                <th className="py-3 px-4 font-medium">Audit Date</th>
                <th className="py-3 px-4 font-medium text-center">Compliance Index</th>
                <th className="py-3 px-4 font-medium">Risk Exposure</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle text-sm">
              {sortedDocs.map((doc) => {
                // Determine styling based on risk level
                const riskStyle =
                  doc.riskLevel === 'high'
                    ? 'text-risk-high bg-risk-high-bg'
                    : doc.riskLevel === 'medium'
                    ? 'text-risk-medium bg-risk-medium-bg'
                    : 'text-risk-low bg-risk-low-bg';

                // Status configuration
                const statusConfig = {
                  completed: {
                    label: 'Verified',
                    icon: <CheckCircle className="w-3.5 h-3.5 text-risk-low inline mr-1" />,
                    class: 'text-risk-low'
                  },
                  flagged: {
                    label: 'Flagged Review',
                    icon: <AlertTriangle className="w-3.5 h-3.5 text-risk-medium inline mr-1" />,
                    class: 'text-risk-medium'
                  },
                  processing: {
                    label: 'Processing...',
                    icon: <span className="w-2 h-2 rounded-full bg-accent-forest animate-pulse inline-block mr-1"></span>,
                    class: 'text-accent-forest italic'
                  },
                  failed: {
                    label: 'OCR Fail',
                    icon: <ShieldAlert className="w-3.5 h-3.5 text-risk-high inline mr-1" />,
                    class: 'text-risk-high font-semibold'
                  }
                }[doc.status];

                return (
                  <tr
                    key={doc.id}
                    id={`doc-row-${doc.id}`}
                    className="hover:bg-bg-card/50 transition-colors group cursor-pointer"
                    onClick={() => onSelectDocument(doc)}
                  >
                    <td className="py-4 px-4 font-sans font-medium text-ink-dark">
                      <div className="flex items-start space-x-2">
                        <FileText className="w-4 h-4 text-ink-muted mt-0.5 group-hover:text-accent-forest transition-colors" />
                        <div>
                          <span className="block underline decoration-transparent group-hover:decoration-accent-forest/40 transition-colors">
                            {doc.name}
                          </span>
                          <span className="block text-xs text-ink-muted font-mono mt-0.5">
                            {doc.fileSize}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-xs font-mono text-ink-muted">
                      {doc.uploadDate}
                    </td>
                    <td className="py-4 px-4 text-center">
                      <span className="font-mono text-sm font-semibold text-ink-dark">
                        {doc.complianceScore}%
                      </span>
                      {/* Quiet scale line */}
                      <div className="w-12 h-1 bg-border-subtle mx-auto mt-1 overflow-hidden">
                        <div
                          className="h-full bg-accent-forest"
                          style={{ width: `${doc.complianceScore}%` }}
                        ></div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`inline-block px-2 py-0.5 text-xs font-mono uppercase font-semibold ${riskStyle}`}>
                        {doc.riskLevel}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-xs font-mono">
                      <div className={`flex items-center ${statusConfig?.class}`}>
                        {statusConfig?.icon}
                        <span>{statusConfig?.label}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end space-x-3">
                        <button
                          id={`delete-btn-${doc.id}`}
                          onClick={() => {
                            if (confirm(`Confirm deletion of ${doc.name}? This action cannot be reversed.`)) {
                              onDeleteDocument(doc.id);
                            }
                          }}
                          className="text-xs font-mono text-ink-muted hover:text-risk-high transition-colors px-1 py-1 cursor-pointer"
                        >
                          Delete
                        </button>
                        <button
                          id={`audit-link-${doc.id}`}
                          onClick={() => onSelectDocument(doc)}
                          className="text-xs font-mono text-accent-forest font-semibold flex items-center space-x-0.5 hover:underline cursor-pointer"
                        >
                          <span>Review</span>
                          <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Trust Badge and Legal Disclaimer footer */}
      <div className="mt-12 text-left border-t border-border-subtle pt-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-ink-muted font-mono" id="dashboard-footer-seal">
        <div className="flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 text-accent-forest" />
          <span>Compliance Framework Certification Active (v2.6)</span>
        </div>
        <div>
          <span>Security Protocol: TLS 1.3 • Data Sovereign Residency</span>
        </div>
      </div>
    </div>
  );
}

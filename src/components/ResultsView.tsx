/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Check, AlertTriangle, AlertCircle, FileText, ChevronRight, Edit2, ShieldCheck, Printer, Save } from 'lucide-react';
import { LegalDocument, ExtractedClause, RiskLevel } from '../types';

interface ResultsViewProps {
  document: LegalDocument;
  onBackToDashboard: () => void;
  onNavigateToReport: () => void;
  onUpdateClause: (clauseId: string, updates: Partial<ExtractedClause>) => void;
  onUpdateDocumentNotes: (notes: string) => void;
}

export default function ResultsView({
  document: initialDoc,
  onBackToDashboard,
  onNavigateToReport,
  onUpdateClause,
  onUpdateDocumentNotes
}: ResultsViewProps) {
  const [doc, setDoc] = useState<LegalDocument>(initialDoc);
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
  const [notes, setNotes] = useState(initialDoc.reviewerNotes || '');
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [editClauseId, setEditClauseId] = useState<string | null>(null);

  // Edit fields for active clause modification
  const [editTitle, setEditTitle] = useState('');
  const [editExplanation, setEditExplanation] = useState('');
  const [editSuggestedAction, setEditSuggestedAction] = useState('');
  const [editRiskLevel, setEditRiskLevel] = useState<RiskLevel>('low');

  // Keep local document synced when parent updates
  useEffect(() => {
    setDoc(initialDoc);
    setNotes(initialDoc.reviewerNotes || '');
  }, [initialDoc]);

  // Handle active clause selection
  const handleClauseClick = (clause: ExtractedClause) => {
    setActiveClauseId(clause.id);
    if (editClauseId !== clause.id) {
      setEditClauseId(null);
    }
  };

  const handleStartEdit = (clause: ExtractedClause) => {
    setEditClauseId(clause.id);
    setEditTitle(clause.title);
    setEditExplanation(clause.explanation);
    setEditSuggestedAction(clause.suggestedAction);
    setEditRiskLevel(clause.riskLevel);
  };

  const handleSaveClauseEdit = (clauseId: string) => {
    onUpdateClause(clauseId, {
      title: editTitle,
      explanation: editExplanation,
      suggestedAction: editSuggestedAction,
      riskLevel: editRiskLevel,
    });
    setEditClauseId(null);
  };

  const handleToggleVerified = (clause: ExtractedClause) => {
    onUpdateClause(clause.id, {
      humanReviewed: !clause.humanReviewed,
      // If marking as verified, automatically quiet down the flag for review
      flaggedForReview: !clause.humanReviewed ? false : clause.flaggedForReview
    });
  };

  const handleSaveNotes = async () => {
    setIsSavingNotes(true);
    await onUpdateDocumentNotes(notes);
    setIsSavingNotes(false);
  };

  // Helper to highlight segments in source text.
  // It takes the document's original text, matches clause texts, and renders them interactively.
  const renderInteractiveText = () => {
    const text = doc.originalText;
    if (!text) return <p className="text-ink-muted">Empty document body.</p>;

    // We can find the occurrences of each clause's text in the original document
    // Sort clauses by their appearance index to parse linearly without breaking offsets
    const sortedClauses = [...doc.clauses].filter(c => c.text && c.text.length > 10).map(c => {
      const idx = text.toLowerCase().indexOf(c.text.substring(0, 40).toLowerCase());
      return { clause: c, startIndex: idx };
    }).filter(item => item.startIndex !== -1)
      .sort((a, b) => a.startIndex - b.startIndex);

    if (sortedClauses.length === 0) {
      return <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-ink-dark select-text">{text}</pre>;
    }

    const segments: React.ReactNode[] = [];
    let lastIndex = 0;

    sortedClauses.forEach((item, index) => {
      const c = item.clause;
      const start = item.startIndex;
      const end = start + c.text.length;

      // Add normal text preceding this highlighted clause
      if (start > lastIndex) {
        segments.push(
          <span key={`text-${index}`} className="select-text">
            {text.substring(lastIndex, start)}
          </span>
        );
      }

      // Add highlighted interactive clause text
      const isActive = activeClauseId === c.id;
      let highlightClass = "bg-border-subtle/40 hover:bg-border-subtle/80 cursor-pointer border-b-2 border-dashed border-ink-muted/30";
      
      if (isActive) {
        highlightClass = c.riskLevel === 'high' 
          ? "bg-red-200/60 text-risk-high border-b-2 border-solid border-risk-high font-medium"
          : c.riskLevel === 'medium'
          ? "bg-amber-200/60 text-risk-medium border-b-2 border-solid border-risk-medium font-medium"
          : "bg-green-200/60 text-risk-low border-b-2 border-solid border-risk-low font-medium";
      } else {
        // quiet highlights for inactive clauses
        highlightClass = c.riskLevel === 'high'
          ? "bg-red-100/30 hover:bg-red-100/60 border-b border-dashed border-risk-high/40 cursor-pointer"
          : c.riskLevel === 'medium'
          ? "bg-amber-100/30 hover:bg-amber-100/60 border-b border-dashed border-risk-medium/40 cursor-pointer"
          : "bg-green-100/30 hover:bg-green-100/60 border-b border-dashed border-risk-low/40 cursor-pointer";
      }

      segments.push(
        <span
          key={`highlight-${c.id}`}
          onClick={() => handleClauseClick(c)}
          title={`Click to view: ${c.title} (${c.riskLevel.toUpperCase()})`}
          className={`inline transition-colors duration-200 px-0.5 ${highlightClass}`}
        >
          {text.substring(start, end)}
        </span>
      );

      lastIndex = end;
    });

    // Add trailing document text
    if (lastIndex < text.length) {
      segments.push(
        <span key="text-trailing" className="select-text">
          {text.substring(lastIndex)}
        </span>
      );
    }

    return (
      <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-ink-dark select-text">
        {segments}
      </pre>
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8" id="results-workspace">
      
      {/* Top action controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border-subtle pb-4 mb-6" id="results-actions-top">
        <button
          id="results-back-btn"
          onClick={onBackToDashboard}
          className="flex items-center space-x-1.5 text-xs text-ink-muted font-mono uppercase tracking-wider hover:text-ink-dark transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Exit Document Workspace</span>
        </button>

        <div className="flex items-center space-x-3" id="results-export-actions">
          <button
            id="results-memo-btn"
            onClick={onNavigateToReport}
            className="border border-accent-forest hover:bg-accent-forest-light text-accent-forest text-xs font-mono uppercase tracking-wider px-4 py-2 flex items-center space-x-1.5 transition-colors cursor-pointer font-semibold"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Generate Executive Memo</span>
          </button>
        </div>
      </div>

      {/* Grid: Left Pane (Source Contract), Right Pane (Analysis & Sidebar) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8" id="results-grid">
        
        {/* Left Pane - Document Reader Experience */}
        <div className="lg:col-span-7 flex flex-col" id="document-source-pane">
          <div className="bg-bg-card border border-border-subtle p-3 flex items-center justify-between text-xs font-mono uppercase tracking-wider text-ink-muted mb-3" id="source-doc-banner">
            <div className="flex items-center space-x-1.5">
              <FileText className="w-3.5 h-3.5" />
              <span>Source Document View</span>
            </div>
            <span>Double-click text to highlight</span>
          </div>

          <div className="bg-[#fcfcf9] border border-border-subtle p-8 shadow-[0_1px_4px_rgba(0,0,0,0.02)] min-h-[600px] max-h-[800px] overflow-y-auto text-left relative" id="sheet-paper">
            {/* Soft vertical watermarks */}
            <div className="absolute right-4 top-4 font-mono text-[10px] text-ink-muted/30 uppercase tracking-widest pointer-events-none select-none">
              Legal Analyzer Certified
            </div>
            {renderInteractiveText()}
          </div>
        </div>

        {/* Right Pane - Active Analysis Workspace */}
        <div className="lg:col-span-5 space-y-6 flex flex-col max-h-[850px] overflow-y-auto pr-1" id="analysis-sidebar-pane">
          
          {/* Plain English Summary Segment */}
          <div className="bg-accent-forest-light border border-accent-forest/15 p-5 text-left" id="executive-summary-block">
            <div className="flex items-center space-x-1.5 mb-2">
              <span className="text-xs font-mono uppercase tracking-wider text-accent-forest font-bold">EXECUTIVE COMPLIANCE SUMMARY</span>
            </div>
            <p className="font-serif text-sm leading-relaxed text-ink-dark">
              {doc.summary}
            </p>
          </div>

          {/* Compliance Rating Metrics */}
          <div className="border border-border-subtle p-5 bg-bg-card grid grid-cols-2 gap-4 text-left" id="document-metrics-summary">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted">Compliance Index</span>
              <div className="flex items-baseline space-x-1.5 mt-1">
                <span className="font-serif text-3xl font-light text-ink-dark">{doc.complianceScore}%</span>
                <span className="text-xs font-mono text-ink-muted">/ 100</span>
              </div>
              <div className="w-full h-1.5 bg-border-subtle mt-2 overflow-hidden">
                <div 
                  className={`h-full ${doc.riskLevel === 'high' ? 'bg-risk-high' : doc.riskLevel === 'medium' ? 'bg-risk-medium' : 'bg-risk-low'}`}
                  style={{ width: `${doc.complianceScore}%` }}
                ></div>
              </div>
            </div>

            <div>
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted">Overall Risk Exposure</span>
              <div className="mt-1">
                <span className={`inline-block px-2.5 py-0.5 text-xs font-mono uppercase font-semibold ${
                  doc.riskLevel === 'high' 
                    ? 'text-risk-high bg-risk-high-bg' 
                    : doc.riskLevel === 'medium' 
                    ? 'text-risk-medium bg-risk-medium-bg' 
                    : 'text-risk-low bg-risk-low-bg'
                }`}>
                  {doc.riskLevel} exposure
                </span>
              </div>
              <span className="text-[11px] text-ink-muted font-mono block mt-2">
                Engine Confidence: {doc.reviewConfidence}%
              </span>
            </div>
          </div>

          {/* Section: Clauses List */}
          <div className="space-y-4 text-left" id="extracted-clauses-wrapper">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2 mb-2" id="clauses-header">
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-bold">Identified Contract Clauses ({doc.clauses.length})</span>
              <span className="text-[11px] text-ink-muted font-mono">Select a highlighted section on the left</span>
            </div>

            <div className="space-y-3" id="clauses-list">
              {doc.clauses.map((clause) => {
                const isActive = activeClauseId === clause.id;
                const isEditing = editClauseId === clause.id;

                const riskColorClass = 
                  clause.riskLevel === 'high' 
                    ? 'text-risk-high border-risk-high bg-risk-high-bg' 
                    : clause.riskLevel === 'medium' 
                    ? 'text-risk-medium border-risk-medium bg-risk-medium-bg' 
                    : 'text-risk-low border-risk-low bg-risk-low-bg';

                return (
                  <div
                    key={clause.id}
                    id={`clause-card-${clause.id}`}
                    onClick={() => handleClauseClick(clause)}
                    className={`border transition-all text-left p-4 ${
                      isActive 
                        ? 'border-accent-forest bg-[#fafafa] shadow-[0_1px_5px_rgba(0,0,0,0.03)]' 
                        : 'border-border-subtle hover:border-ink-muted/30 bg-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-serif text-sm font-semibold text-ink-dark">
                          {clause.title}
                        </span>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted bg-border-subtle px-1.5 py-0.5">
                          {clause.category}
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 text-[10px] font-mono uppercase font-semibold border ${riskColorClass}`}>
                        {clause.riskLevel}
                      </span>
                    </div>

                    {isEditing ? (
                      /* Active Clause Editor */
                      <div className="space-y-3 mt-3 pt-3 border-t border-border-subtle" onClick={(e) => e.stopPropagation()}>
                        <div className="space-y-1">
                          <label className="block text-[10px] font-mono uppercase tracking-wider text-ink-muted">Clause Title</label>
                          <input 
                            type="text" 
                            value={editTitle} 
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="w-full bg-transparent border border-border-subtle p-1.5 text-xs font-sans rounded-none focus:outline-none focus:border-accent-forest"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="block text-[10px] font-mono uppercase tracking-wider text-ink-muted">Risk Assessment Explanation</label>
                          <textarea 
                            rows={3} 
                            value={editExplanation} 
                            onChange={(e) => setEditExplanation(e.target.value)}
                            className="w-full bg-transparent border border-border-subtle p-1.5 text-xs font-sans rounded-none focus:outline-none focus:border-accent-forest leading-relaxed"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="block text-[10px] font-mono uppercase tracking-wider text-ink-muted">Suggested Rev / Drafting Revision</label>
                          <textarea 
                            rows={3} 
                            value={editSuggestedAction} 
                            onChange={(e) => setEditSuggestedAction(e.target.value)}
                            className="w-full bg-transparent border border-border-subtle p-1.5 text-xs font-sans rounded-none focus:outline-none focus:border-accent-forest leading-relaxed"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-2 pt-1">
                          <div className="flex items-center space-x-1.5 text-xs font-mono">
                            <span className="text-ink-muted">Risk Level:</span>
                            <select 
                              value={editRiskLevel} 
                              onChange={(e) => setEditRiskLevel(e.target.value as RiskLevel)}
                              className="bg-transparent border border-border-subtle px-1 py-0.5 cursor-pointer text-ink-dark font-semibold"
                            >
                              <option value="low">LOW</option>
                              <option value="medium">MEDIUM</option>
                              <option value="high">HIGH</option>
                            </select>
                          </div>
                          <div className="flex items-center space-x-2">
                            <button 
                              onClick={() => setEditClauseId(null)}
                              className="text-xs font-mono text-ink-muted hover:text-ink-dark px-2 py-1 border border-border-subtle"
                            >
                              Cancel
                            </button>
                            <button 
                              onClick={() => handleSaveClauseEdit(clause.id)}
                              className="text-xs font-mono text-white bg-accent-forest hover:bg-opacity-90 px-3 py-1 font-semibold"
                            >
                              Save Changes
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Read-only details segment */
                      <div className="space-y-2 mt-2">
                        {isActive && (
                          <div className="bg-bg-card p-3 border-l-2 border-ink-muted/30 text-xs text-ink-muted leading-relaxed font-serif italic" id="clause-source-quote">
                            "{clause.text}"
                          </div>
                        )}
                        <p className="text-xs text-ink-dark/90 leading-relaxed font-sans">
                          <strong className="text-ink-dark block text-[11px] font-mono uppercase tracking-wider mb-0.5">Assessment:</strong>
                          {clause.explanation}
                        </p>
                        <p className="text-xs text-ink-dark/90 leading-relaxed font-sans bg-accent-forest-light/60 p-2 border border-accent-forest/10">
                          <strong className="text-accent-forest block text-[11px] font-mono uppercase tracking-wider mb-0.5">Reciprocal Draft:</strong>
                          {clause.suggestedAction}
                        </p>

                        {/* Interactive Verification Panel */}
                        <div className="flex items-center justify-between border-t border-border-subtle/70 pt-2 mt-2" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center space-x-3">
                            <button
                              id={`toggle-verify-${clause.id}`}
                              onClick={() => handleToggleVerified(clause)}
                              className={`text-xs font-mono flex items-center space-x-1 px-2 py-0.5 border ${
                                clause.humanReviewed
                                  ? 'bg-risk-low-bg text-risk-low border-risk-low/30 font-semibold'
                                  : 'hover:bg-bg-card text-ink-muted border-border-subtle'
                              } transition-colors cursor-pointer`}
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>{clause.humanReviewed ? 'Reviewed' : 'Awaiting Review'}</span>
                            </button>
                            
                            {clause.flaggedForReview && !clause.humanReviewed && (
                              <span className="text-[10px] text-risk-high font-mono flex items-center space-x-0.5 animate-pulse">
                                <AlertTriangle className="w-3 h-3" />
                                <span>FLAGGED REVIEW</span>
                              </span>
                            )}
                          </div>

                          <button
                            id={`edit-clause-btn-${clause.id}`}
                            onClick={() => handleStartEdit(clause)}
                            className="text-xs font-mono text-ink-muted hover:text-accent-forest transition-colors flex items-center space-x-0.5 cursor-pointer"
                          >
                            <Edit2 className="w-3 h-3" />
                            <span>Edit</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section: Overall Audit Notes / Human Override */}
          <div className="border border-border-subtle p-5 bg-transparent text-left space-y-3" id="audit-notes-editor-block">
            <div className="flex items-center justify-between border-b border-border-subtle pb-2">
              <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-bold">Reviewer's Sovereign Commentary</span>
              <button
                id="save-reviewer-notes-btn"
                onClick={handleSaveNotes}
                disabled={isSavingNotes}
                className="text-xs font-mono text-accent-forest hover:underline flex items-center space-x-1 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{isSavingNotes ? 'Saving...' : 'Save Notes'}</span>
              </button>
            </div>
            <textarea
              id="reviewer-sovereign-notes"
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add overarching comments, legal caveats, or client-specific conditions to this contract analysis dossier..."
              className="w-full bg-transparent border border-border-subtle p-3 text-xs font-sans rounded-none focus:outline-none focus:border-accent-forest transition-colors leading-relaxed"
            ></textarea>
            <span className="text-[10px] text-ink-muted font-mono leading-tight block">
              Commentary saved here persists globally and is compiled into the printable audit memo.
            </span>
          </div>

        </div>

      </div>
    </div>
  );
}

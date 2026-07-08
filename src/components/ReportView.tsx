/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { ArrowLeft, Printer, Copy, Check, FileText, Bookmark } from 'lucide-react';
import { LegalDocument } from '../types';

interface ReportViewProps {
  document: LegalDocument;
  onBackToWorkspace: () => void;
}

export default function ReportView({ document, onBackToWorkspace }: ReportViewProps) {
  const [copied, setCopied] = useState(false);
  const memo = document.reportMemo;

  const handlePrint = () => {
    window.print();
  };

  const handleCopyMarkdown = () => {
    // Generate clean markdown content for clipboard export
    const markdown = `
# LEGAL COMPLIANCE AUDIT MEMORANDUM

**TO:** Senior Leadership / Client Advisory Group
**FROM:** Legal Analyzer Sovereign Auditing System
**DATE:** ${memo.date}
**DOCUMENT:** ${document.name}
**COMPLIANCE INDEX:** ${memo.complianceScore}% / 100
**OVERALL RISK LEVEL:** ${document.riskLevel.toUpperCase()}

---

## 1. EXECUTIVE COMPLIANCE SUMMARY
${memo.executiveSummary}

${document.reviewerNotes ? `\n## 2. REVIEWS & ADDITIONAL COMMENTS\n${document.reviewerNotes}` : ''}

## 3. AUDITING RECOMMENDATIONS & NEGOTIATING POSITIONS
${memo.recommendations.map((rec, idx) => `${idx + 1}. ${rec}`).join('\n')}

## 4. DETAILED FINDINGS & CLAUSE ASSESSMENT
${document.clauses.map((clause, idx) => `
### Finding ${idx + 1}: ${clause.title} (${clause.category.toUpperCase()})
- **Risk Rating:** ${clause.riskLevel.toUpperCase()}
- **Original Wording:** "${clause.text}"
- **Assessment:** ${clause.explanation}
- **Proposed Counter-revision:** ${clause.suggestedAction}
- **Human Verification State:** ${clause.humanReviewed ? 'VERIFIED' : 'AWAITING RE-VERIFICATION'}
`).join('\n')}

---
*Confidentiality Notice: This report represents automated and reviewer advisory parameters. It does not constitute formal licensed attorney-client privilege representation.*
    `.trim();

    navigator.clipboard.writeText(markdown).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 text-left" id="report-view-container">
      {/* Upper action bar, invisible during page printing */}
      <div className="flex items-center justify-between border-b border-border-subtle pb-4 mb-8 print:hidden" id="report-header-actions">
        <button
          id="report-back-btn"
          onClick={onBackToWorkspace}
          className="flex items-center space-x-1.5 text-xs text-ink-muted font-mono uppercase tracking-wider hover:text-ink-dark transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Workspace</span>
        </button>

        <div className="flex items-center space-x-3" id="report-utility-controls">
          <button
            id="copy-markdown-btn"
            onClick={handleCopyMarkdown}
            className="border border-border-subtle hover:bg-bg-card text-ink-dark text-xs font-mono uppercase tracking-wider px-4 py-2 flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-risk-low" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
          </button>

          <button
            id="print-pdf-btn"
            onClick={handlePrint}
            className="bg-accent-forest hover:bg-opacity-90 text-white text-xs font-mono uppercase tracking-wider px-4 py-2 flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {/* Styled Printed Sheet */}
      <div 
        id="printed-memorandum-sheet"
        className="bg-white border border-border-subtle p-12 shadow-[0_1px_5px_rgba(0,0,0,0.02)] print:border-0 print:p-0 font-serif text-ink-dark select-text leading-relaxed"
      >
        {/* Document Seal / Header */}
        <div className="border-b-4 border-ink-dark pb-6 mb-8 text-left" id="printed-header-block">
          <div className="flex items-center justify-between mb-4">
            <span className="font-mono text-xs uppercase tracking-widest text-ink-muted">Sovereign Compliance Advisory Dossier</span>
            <span className="font-mono text-xs uppercase tracking-widest text-ink-muted">ID: {document.id}</span>
          </div>
          <h1 className="font-serif text-3xl font-bold uppercase tracking-tight text-ink-dark">
            Memorandum of Audit
          </h1>
        </div>

        {/* Audit Metadata Box */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 bg-bg-card p-6 border border-border-subtle text-xs font-mono uppercase tracking-wider text-left mb-8" id="printed-metadata-grid">
          <div>
            <span className="text-ink-muted block text-[10px]">TO</span>
            <span className="text-ink-dark block mt-1 font-semibold">Corporate Leadership</span>
          </div>
          <div>
            <span className="text-ink-muted block text-[10px]">FROM</span>
            <span className="text-ink-dark block mt-1 font-semibold">Legal Analyzer</span>
          </div>
          <div>
            <span className="text-ink-muted block text-[10px]">DATE</span>
            <span className="text-ink-dark block mt-1 font-semibold">{memo.date}</span>
          </div>
          <div>
            <span className="text-ink-muted block text-[10px]">RATING</span>
            <span className={`block mt-1 font-bold ${document.riskLevel === 'high' ? 'text-risk-high' : 'text-ink-dark'}`}>
              {document.riskLevel.toUpperCase()} RISK ({memo.complianceScore}%)
            </span>
          </div>
        </div>

        {/* Section: Overview */}
        <div className="space-y-6" id="printed-sections">
          <div className="space-y-2 text-left" id="printed-section-executive">
            <h2 className="font-serif text-lg font-bold uppercase tracking-wide border-b border-border-subtle pb-1 text-ink-dark">
              1. Executive Compliance Summary
            </h2>
            <p className="text-sm leading-relaxed text-ink-dark font-sans pt-1">
              {memo.executiveSummary}
            </p>
          </div>

          {/* Overarching commentary if present */}
          {document.reviewerNotes && (
            <div className="space-y-2 text-left" id="printed-section-commentary">
              <h2 className="font-serif text-lg font-bold uppercase tracking-wide border-b border-border-subtle pb-1 text-ink-dark">
                2. Auditor Reviewer Commentary
              </h2>
              <p className="text-sm leading-relaxed text-ink-dark font-sans whitespace-pre-wrap bg-bg-card/40 p-4 border border-border-subtle/50 italic">
                {document.reviewerNotes}
              </p>
            </div>
          )}

          {/* Section: Strategic Recommendations */}
          <div className="space-y-2 text-left" id="printed-section-recommendations">
            <h2 className="font-serif text-lg font-bold uppercase tracking-wide border-b border-border-subtle pb-1 text-ink-dark">
              {document.reviewerNotes ? '3.' : '2.'} Negotiating Actions & Recommendations
            </h2>
            <ol className="list-decimal list-inside space-y-2.5 text-sm font-sans pt-1">
              {memo.recommendations.map((rec, idx) => (
                <li key={idx} className="leading-relaxed pl-1">
                  {rec}
                </li>
              ))}
            </ol>
          </div>

          {/* Section: Findings Table */}
          <div className="space-y-4 pt-4 text-left" id="printed-section-findings">
            <h2 className="font-serif text-lg font-bold uppercase tracking-wide border-b border-border-subtle pb-1 text-ink-dark">
              {document.reviewerNotes ? '4.' : '3.'} Detailed Contract Findings
            </h2>

            <div className="space-y-6 pt-2" id="printed-findings-list">
              {document.clauses.map((clause, idx) => {
                const riskRatingStyle = 
                  clause.riskLevel === 'high' 
                    ? 'text-risk-high border-risk-high bg-risk-high-bg' 
                    : clause.riskLevel === 'medium' 
                    ? 'text-risk-medium border-risk-medium bg-risk-medium-bg' 
                    : 'text-risk-low border-risk-low bg-risk-low-bg';

                return (
                  <div key={clause.id} id={`printed-clause-${clause.id}`} className="border-b border-border-subtle pb-6 last:border-0 last:pb-0 text-left">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <h4 className="font-serif text-base font-bold text-ink-dark">
                        {idx + 1}. Finding: {clause.title}
                      </h4>
                      <span className={`px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider font-semibold border ${riskRatingStyle}`}>
                        {clause.riskLevel}
                      </span>
                    </div>

                    <div className="space-y-3 text-xs text-ink-dark/90 font-sans" id={`finding-details-${idx}`}>
                      <div className="bg-bg-card p-3 border-l-2 border-border-subtle font-serif text-xs italic text-ink-muted">
                        "{clause.text}"
                      </div>
                      <p className="leading-relaxed">
                        <strong className="font-mono uppercase text-[10px] tracking-wider text-ink-muted block mb-0.5">Assessment:</strong>
                        {clause.explanation}
                      </p>
                      <p className="leading-relaxed bg-accent-forest-light/30 p-2.5 border border-accent-forest/10">
                        <strong className="font-mono uppercase text-[10px] tracking-wider text-accent-forest block mb-0.5">Proposed Drafting Revision:</strong>
                        {clause.suggestedAction}
                      </p>
                      <div className="flex items-center justify-between text-[10px] font-mono text-ink-muted border-t border-border-subtle/40 pt-1.5">
                        <span>Category: {clause.category.toUpperCase()}</span>
                        <span>Auditor Verification State: {clause.humanReviewed ? 'VERIFIED BY COUNSEL' : 'AUTOMATED CLASSIFICATION'}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Legal Disclaimer block */}
        <div className="border-t border-border-subtle mt-12 pt-6 text-[10px] text-ink-muted font-mono leading-relaxed text-left" id="printed-disclaimer">
          <p>
            CONFIDENTIALITY NOTICE: This compliance memo contains privileged, automated analytical advisory criteria. It is generated securely utilizing machine-learning clause parsers and is intended for licensed professional review, not as direct replacement for licensed attorney-client advisory retainers.
          </p>
        </div>
      </div>
    </div>
  );
}

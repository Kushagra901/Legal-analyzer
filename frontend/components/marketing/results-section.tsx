/**
 * @file results-section.tsx
 * @description Renders Image 5: Interactive split-pane results demonstrating synchronized
 * primary source drafting versus automated synthesis, plus the 3-column redline replacement
 * workbench card showing Original Clause, Suggested Replacement, and Why.
 */

import React from "react";

export function ResultsSection() {
  return (
    <section className="w-full max-w-5xl mx-auto py-16 sm:py-24 border-t border-[#E5E5E0] space-y-16 sm:space-y-20">
      {/* ------------------------------------------------------------- */}
      {/* PART 1: Interactive Split-Pane Results                         */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-8">
        <div className="space-y-3">
          <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#6B7280] block">
            RESULTS
          </span>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#0D1B2A] tracking-tight">
            Interactive split-pane results
          </h2>
          <p className="text-xs sm:text-sm text-[#595959] leading-relaxed font-sans max-w-2xl">
            Inspect the original contract text alongside parsed clauses, risk severity indicators,
            statutory citations and NDA compliance violations.
          </p>
        </div>

        {/* Dual-Pane Card */}
        <div className="bg-white border border-[#E5E5E0] shadow-xs overflow-hidden">
          {/* Card Chrome Bar */}
          <div className="bg-[#FAF9F5] border-b border-[#E5E5E0] px-4 py-2.5 flex items-center justify-between text-[10px] font-mono text-[#6B7280]">
            <span className="font-semibold text-[#1C1C1C] uppercase tracking-wider">
              Synchronized Dual-Pane Analysis
            </span>
            <span className="text-[9px] tracking-widest text-[#9CA3AF] uppercase">
              ILLUSTRATIVE EXAMPLE
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2">
            {/* Left Pane: Primary Source Drafting */}
            <div className="p-6 border-b md:border-b-0 md:border-r border-[#E5E5E0] space-y-4 bg-white">
              <div className="flex items-center justify-between pb-2 border-b border-[#F3F4F6] text-[9px] font-mono uppercase tracking-wider text-[#6B7280]">
                <span>PRIMARY SOURCE DRAFTING</span>
                <span>CLAUSE 8.3</span>
              </div>

              <p className="text-xs text-[#6B7280] leading-relaxed font-serif">
                8.2 Term. This Agreement shall commence on the Effective Date and remain in effect
                for two (2) years unless earlier terminated in accordance with Section 8.3.
              </p>

              {/* Highlighted Violation Box */}
              <div className="bg-[#FEF2F2] border border-[#FECACA] p-4 text-left space-y-1.5">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#991B1B]">
                  VIOLATION: ASYMMETRIC TERMINATION RIGHTS
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  &ldquo;8.3 Termination for Convenience. Provider may terminate this Agreement at
                  any time without cause upon thirty (30) days&apos; prior written notice. Customer
                  shall have no right of termination for convenience.&rdquo;
                </p>
              </div>

              <p className="text-xs text-[#6B7280] leading-relaxed font-serif">
                8.4 Effect of Termination. Upon termination, Customer shall immediately remit all
                accrued fees within ten (10) calendar days.
              </p>
            </div>

            {/* Right Pane: Automated Synthesis & Precedents */}
            <div className="p-6 space-y-4 bg-[#FAF9F5] flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-[#E5E5E0] text-[9px] font-mono uppercase tracking-wider">
                  <span className="text-[#6B7280]">AUTOMATED SYNTHESIS &amp; PRECEDENTS</span>
                  <span className="font-bold text-[#991B1B]">CRITICAL ISSUE</span>
                </div>

                <div className="bg-white border border-[#E5E5E0] p-4 space-y-3">
                  <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#991B1B]">
                    DEFICIENCY: ONE-SIDED TERMINATION FOR CONVENIENCE
                  </div>
                  <p className="text-xs text-[#374151] leading-relaxed font-sans">
                    Provider retains unilateral cancellation power while locking Customer into
                    minimum 24-month fee commitments. Departs from commercial standard terms.
                  </p>

                  <div className="space-y-1.5 pt-2 border-t border-[#F3F4F6] text-[11px] font-mono">
                    <div className="flex items-center justify-between text-[#6B7280]">
                      <span>References:</span>
                      <span className="text-[#1C1C1C]">[citation]</span>
                    </div>
                    <div className="flex items-center justify-between text-[#6B7280]">
                      <span>Playbook rule:</span>
                      <span className="text-[#1C1C1C]">Mutual notice period recommended</span>
                    </div>
                    <div className="flex items-center justify-between text-[#991B1B] font-bold">
                      <span>Score impact:</span>
                      <span>-15 points</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Bar */}
          <div className="bg-[#FAF9F5] border-t border-[#E5E5E0] px-4 py-2.5 flex items-center justify-between text-[11px] font-mono text-[#6B7280]">
            <span>Status: Review in progress.</span>
            <span className="font-semibold text-[#0D1B2A]">Document score: 60 / 100</span>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* PART 2: Suggested Replacement Text (Redlines)                 */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-6">
        <div className="flex items-baseline justify-between">
          <div className="space-y-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#6B7280] block">
              REDLINES
            </span>
            <h3 className="font-serif text-2xl sm:text-3xl text-[#0D1B2A] tracking-tight">
              Suggested replacement text, with the reasoning.
            </h3>
          </div>
          <span className="text-[9px] font-mono text-[#9CA3AF] tracking-widest uppercase hidden sm:inline">
            ILLUSTRATIVE EXAMPLE
          </span>
        </div>

        {/* 3-Column Redlines Card */}
        <div className="bg-white border border-[#E5E5E0] p-6 sm:p-8 shadow-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 divide-y md:divide-y-0 md:divide-x divide-[#E5E5E0]">
            {/* Column 1: Original Clause */}
            <div className="space-y-3 pt-4 md:pt-0">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#6B7280] block">
                ORIGINAL CLAUSE
              </span>
              <p className="text-xs sm:text-[13px] font-serif text-[#1C1C1C] leading-relaxed italic">
                &ldquo;Provider may terminate at any time without cause on thirty days&apos; notice;
                Customer has no right of termination.&rdquo;
              </p>
              <span className="text-[10px] font-mono text-[#9CA3AF] block pt-2">
                Clause 8.3
              </span>
            </div>

            {/* Column 2: Suggested Replacement */}
            <div className="space-y-3 pt-6 md:pt-0 md:pl-8">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#6B7280] block">
                SUGGESTED REPLACEMENT
              </span>
              <p className="text-xs sm:text-[13px] font-serif text-[#0D1B2A] font-semibold leading-relaxed">
                &ldquo;Either party may terminate for convenience on thirty days&apos; written
                notice.&rdquo;
              </p>
              <span className="text-[10px] font-mono text-[#166534] block pt-2 font-medium">
                Balanced drafting
              </span>
            </div>

            {/* Column 3: Why */}
            <div className="space-y-3 pt-6 md:pt-0 md:pl-8">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#6B7280] block">
                WHY
              </span>
              <p className="text-xs sm:text-[13px] text-[#374151] leading-relaxed font-sans">
                Makes the termination right mutual.
              </p>
              <span className="text-[10px] font-mono text-[#6B7280] block pt-2">
                Playbook alignment
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

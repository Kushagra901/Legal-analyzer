/**
 * @file hero-mockup.tsx
 * @description Interactive split-pane product mockup matching Image 1:
 * Left pane displays Master Services Agreement source contract with color-coded
 * flagged clause excerpts. Right pane displays the Clause Triage Queue with scored
 * risk deductions and cumulative document score (60 / 100).
 */

"use client";

import React from "react";
import { motion, useInView } from "framer-motion";

export function HeroMockup() {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, amount: 0.15 });

  return (
    <div ref={containerRef} className="w-full max-w-5xl mx-auto">
      {/* Mockup Frame Container */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="bg-white border border-[#E5E5E0] shadow-[0_2px_12px_rgba(0,0,0,0.04),0_12px_32px_rgba(0,0,0,0.06)] overflow-hidden"
      >
        {/* Top Header Bar */}
        <div className="bg-[#FAF9F5] border-b border-[#E5E5E0] px-4 py-2.5 flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-[#6B7280]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#166534]" />
            <span className="font-semibold text-[#1C1C1C]">
              SAMPLE CONTRACT — MASTER SERVICES AGREEMENT
            </span>
          </div>
          <span className="text-[9px] text-[#9CA3AF] tracking-widest">
            ILLUSTRATIVE EXAMPLE
          </span>
        </div>

        {/* Split-Pane Content */}
        <div className="grid grid-cols-1 md:grid-cols-12 min-h-[540px]">
          {/* ------------------------------------------------------------- */}
          {/* LEFT PANE (7 cols / ~58% width): Contract Text with Highlights */}
          {/* ------------------------------------------------------------- */}
          <div className="md:col-span-7 p-5 sm:p-7 border-b md:border-b-0 md:border-r border-[#E5E5E0] bg-white flex flex-col justify-between">
            <div className="space-y-4">
              {/* Header inside pane */}
              <div className="flex items-center justify-between pb-2 border-b border-[#F3F4F6] text-[9px] font-mono uppercase tracking-wider text-[#6B7280]">
                <span>SECTION 11 — INDEMNIFICATION & LIMITATION OF LIABILITY</span>
                <span>PARAGRAPH 11.2</span>
              </div>

              {/* Standard text */}
              <p className="text-xs text-[#4B5563] leading-relaxed font-serif">
                11.1 Each party shall hold harmless the other party against third-party claims
                arising solely from gross negligence.
              </p>

              {/* Box 1: High Risk Unilateral Obligation */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 1 } : { opacity: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="bg-[#FEF2F2] border border-[#FECACA] p-3 text-left"
              >
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#991B1B] mb-1">
                  UNILATERAL OBLIGATION [HIGH RISK]
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  11.2 &ldquo;Customer agrees to defend, indemnify, and hold harmless Provider from
                  all liabilities, damages, and settlements arising out of any third-party claim,
                  without cap or reciprocal duty, regardless of negligence or fault.&rdquo;
                </p>
              </motion.div>

              {/* Box 2: High Risk Asymmetric Termination */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 1 } : { opacity: 0 }}
                transition={{ duration: 0.5, delay: 0.45 }}
                className="bg-[#FEF2F2] border border-[#FECACA] p-3 text-left"
              >
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#991B1B] mb-1">
                  ASYMMETRIC TERMINATION [HIGH RISK]
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  8.3 &ldquo;Provider may terminate this Agreement at any time without cause upon
                  thirty (30) days&apos; prior written notice. Customer shall have no right of
                  termination for convenience.&rdquo;
                </p>
              </motion.div>

              {/* Box 3: Medium Risk Non-Standard Period */}
              <div className="bg-[#FEFCE8] border border-[#FEF08A] p-3 text-left">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#854D0E] mb-1">
                  NON-STANDARD PERIOD [MEDIUM RISK]
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  12.4 &ldquo;Survival of Confidentiality obligations shall endure for an indefinite
                  period following termination or expiry of this Agreement.&rdquo;
                </p>
              </div>

              {/* Box 4: Medium Risk Broad Non-Solicitation */}
              <div className="bg-[#FEFCE8] border border-[#FEF08A] p-3 text-left">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#854D0E] mb-1">
                  BROAD NON-SOLICITATION [MEDIUM RISK]
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  13.1 &ldquo;Neither party shall solicit for employment any employee of the other
                  party during the term and for 24 months thereafter.&rdquo;
                </p>
              </div>

              {/* Box 5: Low Risk Governing Law */}
              <div className="bg-[#F0FDF4] border border-[#BBF7D0] p-3 text-left">
                <div className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#166534] mb-1">
                  GOVERNING LAW [LOW RISK]
                </div>
                <p className="text-xs font-serif text-[#1C1C1C] leading-relaxed">
                  16.2 &ldquo;This Agreement shall be governed by Delaware law with standard venue
                  and severability provisions.&rdquo;
                </p>
              </div>
            </div>
          </div>

          {/* ------------------------------------------------------------- */}
          {/* RIGHT PANE (5 cols / ~42% width): Clause Triage Queue         */}
          {/* ------------------------------------------------------------- */}
          <div className="md:col-span-5 p-5 sm:p-6 bg-[#FAF9F5] flex flex-col justify-between">
            <div className="space-y-3.5">
              {/* Header inside pane */}
              <div className="flex items-center justify-between pb-2 border-b border-[#E5E5E0] text-[9px] font-mono uppercase tracking-wider text-[#6B7280]">
                <span>CLAUSE TRIAGE QUEUE</span>
                <span className="font-bold text-[#991B1B]">4 FLAGGED</span>
              </div>

              {/* Card 1: High Severity */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                className="bg-white border border-[#E5E5E0] p-3.5 text-left shadow-xs"
              >
                <div className="flex items-center justify-between text-[9px] font-mono uppercase tracking-wider mb-1">
                  <span className="text-[#991B1B] font-bold flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 bg-[#991B1B]" />
                    HIGH SEVERITY
                  </span>
                  <span className="text-[#991B1B] font-bold font-mono">-15 points</span>
                </div>
                <h4 className="font-serif font-bold text-xs text-[#0D1B2A] mb-1">
                  11.2 Indemnification & third-party claims
                </h4>
                <p className="text-[11px] text-[#4B5563] leading-relaxed font-sans mb-2">
                  Unilateral, uncapped customer defense lacking reciprocal indemnification
                  obligations.
                </p>
                <div className="flex items-center justify-between text-[9px] font-mono text-[#6B7280] pt-1.5 border-t border-[#F3F4F6]">
                  <span>Reference: [citation]</span>
                  <span className="text-[#991B1B] font-semibold">Flagged</span>
                </div>
              </motion.div>

              {/* Card 2: High Severity */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
                transition={{ duration: 0.5, delay: 0.45 }}
                className="bg-white border border-[#E5E5E0] p-3.5 text-left shadow-xs"
              >
                <div className="flex items-center justify-between text-[9px] font-mono uppercase tracking-wider mb-1">
                  <span className="text-[#991B1B] font-bold flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 bg-[#991B1B]" />
                    HIGH SEVERITY
                  </span>
                  <span className="text-[#991B1B] font-bold font-mono">-15 points</span>
                </div>
                <h4 className="font-serif font-bold text-xs text-[#0D1B2A] mb-1">
                  8.3 Termination for convenience
                </h4>
                <p className="text-[11px] text-[#4B5563] leading-relaxed font-sans mb-2">
                  One-sided vendor cancellation right on 30-day notice with no reciprocal customer
                  right.
                </p>
                <div className="flex items-center justify-between text-[9px] font-mono text-[#6B7280] pt-1.5 border-t border-[#F3F4F6]">
                  <span>Reference: [citation]</span>
                  <span className="text-[#991B1B] font-semibold">Flagged</span>
                </div>
              </motion.div>

              {/* Card 3: Medium Severity */}
              <div className="bg-white border border-[#E5E5E0] p-3.5 text-left shadow-xs">
                <div className="flex items-center justify-between text-[9px] font-mono uppercase tracking-wider mb-1">
                  <span className="text-[#854D0E] font-bold flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 bg-[#854D0E]" />
                    MEDIUM SEVERITY
                  </span>
                  <span className="text-[#854D0E] font-bold font-mono">-5 points</span>
                </div>
                <h4 className="font-serif font-bold text-xs text-[#0D1B2A] mb-1">
                  12.4 Confidentiality term & survival
                </h4>
                <p className="text-[11px] text-[#4B5563] leading-relaxed font-sans mb-2">
                  Confidentiality obligation has no end date.
                </p>
                <div className="flex items-center justify-between text-[9px] font-mono text-[#6B7280] pt-1.5 border-t border-[#F3F4F6]">
                  <span>Reference: [citation]</span>
                  <span className="text-[#854D0E] font-semibold">Flagged</span>
                </div>
              </div>

              {/* Card 4: Medium Severity */}
              <div className="bg-white border border-[#E5E5E0] p-3.5 text-left shadow-xs">
                <div className="flex items-center justify-between text-[9px] font-mono uppercase tracking-wider mb-1">
                  <span className="text-[#854D0E] font-bold flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 bg-[#854D0E]" />
                    MEDIUM SEVERITY
                  </span>
                  <span className="text-[#854D0E] font-bold font-mono">-5 points</span>
                </div>
                <h4 className="font-serif font-bold text-xs text-[#0D1B2A] mb-1">
                  13.1 Non-solicitation of personnel
                </h4>
                <p className="text-[11px] text-[#4B5563] leading-relaxed font-sans mb-2">
                  Broad non-solicitation restriction extending 24 months post-termination.
                </p>
                <div className="flex items-center justify-between text-[9px] font-mono text-[#6B7280] pt-1.5 border-t border-[#F3F4F6]">
                  <span>Reference: [citation]</span>
                  <span className="text-[#854D0E] font-semibold">Flagged</span>
                </div>
              </div>
            </div>

            {/* Bottom Overall Score Bar */}
            <div className="pt-4 mt-4 border-t border-[#E5E5E0] flex items-center justify-between text-xs font-mono">
              <span className="text-[#6B7280] uppercase tracking-wider text-[11px]">
                Overall Document Score:
              </span>
              <span className="font-bold text-[#0D1B2A] text-sm tracking-tight">
                60 / 100
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Hero Footnote Tagline (from Image 1 bottom) */}
      <p className="text-center text-xs text-[#6B7280] mt-8 font-serif italic">
        For first-pass review of NDAs, SaaS terms and employment agreements.
      </p>
    </div>
  );
}

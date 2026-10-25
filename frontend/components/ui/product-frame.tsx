/**
 * @file product-frame.tsx
 * @description macOS-style application window product mockup floating on paper background.
 * Split-pane architecture:
 * - Left Pane (60%): White background, serif typography (Newsreader), NDA clause with yellow/brass highlight.
 * - Right Pane (40%): Cream/off-white background (#f9f6f0), stacked clause risk cards.
 * - Chrome: 40px macOS title bar with colored window controls, centered fake URL bar.
 * - Shadow: Large soft drop shadow (shadow-2xl) floating over the page.
 */

"use client";

import React from "react";
import { motion, useInView } from "framer-motion";
import { Lock, AlertTriangle, ShieldAlert, CheckCircle2, ArrowRight } from "lucide-react";

export function ProductFrame() {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, {
    once: true,
    amount: 0.2,
  });

  return (
    <div ref={containerRef} className="w-[90%] max-w-[1200px] mx-auto my-4 sm:my-8">
      {/* macOS Window Frame with shadow-2xl floating on paper background */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="rounded-xl overflow-hidden border border-[#D5D7DC] bg-white shadow-2xl"
      >
        {/* Top Bar: 40px height, light gray, 3 colored dots, centered fake URL */}
        <div className="h-[40px] bg-[#ECEFF2] border-b border-[#D8DBDF] px-4 flex items-center justify-between select-none">
          {/* 3 small dots (Red, Yellow, Green) on the left */}
          <div className="flex items-center gap-2 w-24">
            <span
              className="w-3 h-3 rounded-full bg-[#FF5F56] border border-[#E0443E] shadow-xs"
              title="Close"
            />
            <span
              className="w-3 h-3 rounded-full bg-[#FFBD2E] border border-[#DEA123] shadow-xs"
              title="Minimize"
            />
            <span
              className="w-3 h-3 rounded-full bg-[#27C93F] border border-[#1AAB29] shadow-xs"
              title="Maximize"
            />
          </div>

          {/* Centered fake URL bar */}
          <div className="flex-1 flex justify-center max-w-[420px] mx-auto px-2">
            <div className="h-[26px] w-full max-w-[320px] bg-white/95 border border-[#D0D4DA] rounded-md px-2.5 flex items-center justify-center gap-1.5 shadow-xs">
              <Lock className="w-3 h-3 text-[#6B7280] shrink-0" />
              <span className="text-[11px] font-mono text-[#374151] truncate tracking-tight">
                app.legalanalyzer.com/documents/1
              </span>
            </div>
          </div>

          {/* Right window utility tag */}
          <div className="flex items-center justify-end gap-1.5 w-24">
            <span className="w-2 h-2 rounded-full bg-[var(--risk-low)] animate-pulse" />
            <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] font-semibold hidden sm:inline">
              LIVE PREVIEW
            </span>
          </div>
        </div>

        {/* Split Pane: Left (60% width) / Right (40% width) */}
        <div className="flex flex-col md:flex-row min-h-[460px] md:min-h-[520px]">
          {/* ------------------------------------------------------------- */}
          {/* LEFT PANE (60% width): White bg, Serif font, NDA excerpt     */}
          {/* ------------------------------------------------------------- */}
          <div className="w-full md:w-[60%] bg-white p-6 sm:p-8 md:p-10 border-b md:border-b-0 md:border-r border-[#E5E7EB] flex flex-col justify-between">
            <div>
              {/* Header metadata */}
              <div className="flex items-center justify-between pb-4 mb-6 border-b border-[#F0F2F5]">
                <div className="space-y-0.5">
                  <span className="text-[10px] font-sans font-bold uppercase tracking-widest text-[var(--text-muted)]">
                    CONTRACT EXTRACT • REVISED DRAFT
                  </span>
                  <h2 className="font-serif text-lg sm:text-xl font-bold text-[var(--accent-primary)]">
                    Mutual Nondisclosure Agreement
                  </h2>
                </div>
                <span className="text-[11px] font-mono text-[var(--text-muted)] bg-gray-100 px-2 py-0.5 rounded-sm">
                  Doc ID: #NDA-2026-089
                </span>
              </div>

              {/* Realistic Contract Snippets */}
              <div className="space-y-6 text-[#1c1c1c] font-serif leading-relaxed">
                <div>
                  <h4 className="font-serif font-semibold text-sm sm:text-base text-[var(--accent-primary)] mb-1.5">
                    4. STANDARD OF CARE
                  </h4>
                  <p className="text-xs sm:text-[13px] text-gray-700 leading-relaxed font-serif">
                    The Receiving Party agrees to protect the Disclosing Party&apos;s Confidential
                    Information with the same degree of care it accords to its own confidential
                    information of like nature, but in no event less than a reasonable degree of care.
                  </p>
                </div>

                {/* Target Clause with Yellow/Brass Highlight */}
                <div className="relative pl-3 border-l-2 border-[#b8860b]">
                  <h4 className="font-serif font-bold text-sm sm:text-base text-[var(--accent-primary)] mb-1.5 flex items-center gap-2">
                    5. CONFIDENTIALITY OBLIGATION
                    <span className="font-sans text-[9px] uppercase tracking-wider font-bold bg-[#f5e6b8] text-[#78350f] px-1.5 py-0.5 rounded-xs">
                      Flagged Clause
                    </span>
                  </h4>
                  <p className="text-xs sm:text-[13.5px] leading-relaxed text-[#1c1c1c] font-serif">
                    The Receiving Party shall{" "}
                    <mark className="bg-[#f5e6b8] text-[#1c1c1c] px-1.5 py-0.5 rounded-xs font-medium border-b border-[#d4af37] transition-colors duration-500">
                      hold the Confidential Information in strict confidence
                    </mark>{" "}
                    and shall not disclose, reproduce, or distribute such Confidential Information to
                    any third party without prior express written consent. The Receiving Party
                    acknowledges and covenants that any breach of this Section 5 shall cause
                    irreparable harm, entitling Disclosing Party to immediate injunctive relief and
                    uncapped liquidated damages without proving actual harm.
                  </p>
                </div>

                <div>
                  <h4 className="font-serif font-semibold text-sm sm:text-base text-[var(--accent-primary)] mb-1.5">
                    6. EXCEPTIONS & PERMITTED DISCLOSURES
                  </h4>
                  <p className="text-xs sm:text-[13px] text-gray-700 leading-relaxed font-serif">
                    Confidential Information does not include information that: (a) is or becomes
                    generally known to the public without breach; (b) was already in lawful possession
                    prior to disclosure; or (c) is required to be disclosed under valid judicial process.
                  </p>
                </div>
              </div>
            </div>

            {/* Bottom status line */}
            <div className="pt-6 mt-6 border-t border-[#F0F2F5] flex items-center justify-between text-[11px] font-sans text-[var(--text-muted)]">
              <span>Extracted via Tesseract OCR Engine</span>
              <span>Matched Clause Taxonomy: 41 CUAD Categories</span>
            </div>
          </div>

          {/* ------------------------------------------------------------- */}
          {/* RIGHT PANE (40% width): Light cream/off-white (#f9f6f0)       */}
          {/* ------------------------------------------------------------- */}
          <div className="w-full md:w-[40%] bg-[#f9f6f0] p-5 sm:p-6 md:p-7 flex flex-col justify-between">
            <div>
              {/* Pane Header */}
              <div className="flex items-center justify-between pb-3 mb-5 border-b border-[#E8E5DD]">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-[var(--accent-primary)]" />
                  <span className="font-sans text-xs font-bold uppercase tracking-wider text-[var(--accent-primary)]">
                    Clause Risk Triage
                  </span>
                </div>
                <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                  3 Issues Identified
                </span>
              </div>

              {/* Stacked Clause Cards */}
              <div className="space-y-3.5">
                {/* Card 1: Primary High Risk (as requested) */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
                  transition={{ duration: 0.5, delay: 0.4 }}
                  className="bg-white border border-[#FCA5A5] p-4 shadow-xs"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-serif font-bold text-sm text-[var(--accent-primary)]">
                      Confidentiality Obligation
                    </span>
                    <span className="shrink-0 inline-flex items-center gap-1 bg-[#FEF2F2] text-[#991B1B] border border-[#EF4444] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#DC2626]" />
                      High Risk
                    </span>
                  </div>
                  <p className="text-xs text-[#374151] leading-relaxed mb-3 font-sans">
                    This clause creates an unlimited liability by establishing uncapped liquidated
                    damages and waiving evidentiary requirements for actual damages upon inadvertent
                    disclosure.
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-[#FEE2E2] text-[10px] font-sans">
                    <span className="text-[var(--text-muted)] font-medium">Confidence: 96%</span>
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 font-semibold text-[var(--accent-primary)] hover:underline uppercase tracking-wider text-[9px]"
                    >
                      View Statute & Model Clause
                      <ArrowRight className="w-2.5 h-2.5" />
                    </button>
                  </div>
                </motion.div>

                {/* Card 2: Medium Risk */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
                  transition={{ duration: 0.5, delay: 0.6 }}
                  className="bg-white border border-[#E5E5E0] p-4 shadow-xs"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-serif font-bold text-sm text-[var(--accent-primary)]">
                      Indefinite Survival Term
                    </span>
                    <span className="shrink-0 inline-flex items-center gap-1 bg-[#FEFCE8] text-[#854D0E] border border-[#EAB308] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                      <AlertTriangle className="w-2.5 h-2.5" />
                      Medium Risk
                    </span>
                  </div>
                  <p className="text-xs text-[#4B5563] leading-relaxed font-sans">
                    Perpetual survival of non-trade-secret confidential terms exceeds market norm.
                    Standard recommendation is 2 to 3 years post-termination.
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-[#F3F4F6] text-[10px] font-sans">
                    <span className="text-[var(--text-muted)] font-medium">Confidence: 92%</span>
                    <span className="text-[var(--text-muted)] text-[9px] uppercase tracking-wider">
                      Section 6 Citation
                    </span>
                  </div>
                </motion.div>

                {/* Card 3: Low Risk / Standard */}
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={isInView ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
                  transition={{ duration: 0.5, delay: 0.8 }}
                  className="bg-white border border-[#E5E5E0] p-4 shadow-xs"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-serif font-bold text-sm text-[var(--accent-primary)]">
                      Standard of Care Carve-Out
                    </span>
                    <span className="shrink-0 inline-flex items-center gap-1 bg-[#F0FDF4] text-[#166534] border border-[#22C55E] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      Low Risk
                    </span>
                  </div>
                  <p className="text-xs text-[#4B5563] leading-relaxed font-sans">
                    Reasonable degree of care standard aligns with standard commercial confidentiality
                    jurisprudence and contains customary judicial exceptions.
                  </p>
                </motion.div>
              </div>
            </div>

            {/* Bottom disclaimer note */}
            <div className="pt-4 mt-4 border-t border-[#E8E5DD] text-[10px] text-[var(--text-muted)] leading-tight font-sans">
              AI-assisted triage output calibrated against CUAD 41-clause benchmark. Does not
              constitute formal legal counsel.
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

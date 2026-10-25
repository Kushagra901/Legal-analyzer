/**
 * @file sample-memo-section.tsx
 * @description Renders Image 2: Sample memo presentation.
 * Displays a realistic formal memorandum document floating with a paper shadow,
 * complete with memorandum metadata header, executive summary, flagged provisions table,
 * score rating bar, and download action link.
 */

import React from "react";
import Link from "next/link";

const MEMO_PROVISIONS = [
  {
    clauseRef: "11.2",
    issue: "Indemnification and third-party claims",
    severity: "HIGH",
    severityColor: "text-[#991B1B]",
    scoreImpact: "-15 points",
    impactColor: "text-[#991B1B]",
  },
  {
    clauseRef: "8.3",
    issue: "Termination for convenience",
    severity: "HIGH",
    severityColor: "text-[#991B1B]",
    scoreImpact: "-15 points",
    impactColor: "text-[#991B1B]",
  },
  {
    clauseRef: "12.4",
    issue: "Confidentiality term and survival",
    severity: "MEDIUM",
    severityColor: "text-[#854D0E]",
    scoreImpact: "-5 points",
    impactColor: "text-[#854D0E]",
  },
  {
    clauseRef: "13.1",
    issue: "Non-solicitation of personnel",
    severity: "MEDIUM",
    severityColor: "text-[#854D0E]",
    scoreImpact: "-5 points",
    impactColor: "text-[#854D0E]",
  },
];

export function SampleMemoSection() {
  return (
    <section className="w-full max-w-5xl mx-auto py-16 sm:py-24 border-t border-[#E5E5E0] space-y-12">
      {/* Section Header */}
      <div className="text-center space-y-3">
        <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#6B7280] block">
          REPORT
        </span>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#0D1B2A] tracking-tight">
          Sample memo
        </h2>
        <p className="text-xs sm:text-sm text-[#595959] leading-relaxed font-sans max-w-xl mx-auto">
          A formal triage memo for associate preparation and partner sign-off.
        </p>
      </div>

      {/* Floating Formal Memorandum Document Sheet */}
      <div className="max-w-3xl mx-auto bg-white border border-[#E5E5E0] p-8 sm:p-12 md:p-14 shadow-[0_4px_24px_rgba(0,0,0,0.06),0_1px_3px_rgba(0,0,0,0.03)] text-left space-y-8 font-serif">
        {/* Top Header Tag */}
        <div className="flex justify-between items-center text-[9px] font-mono uppercase tracking-widest text-[#9CA3AF] border-b border-[#F0F2F5] pb-3">
          <span className="font-semibold text-[#6B7280]">CONFIDENTIAL ATTORNEY WORK PRODUCT</span>
          <span>ILLUSTRATIVE EXAMPLE</span>
        </div>

        {/* Memo Header */}
        <div className="space-y-4 border-b border-[#E5E5E0] pb-6">
          <div className="flex justify-between items-baseline">
            <h3 className="font-serif font-bold text-lg tracking-wider text-[#0D1B2A] uppercase">
              MEMORANDUM OF COUNSEL
            </h3>
            <span className="text-[10px] font-mono text-[#6B7280]">DATE: [Date]</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 text-xs font-sans pt-2">
            <div>
              <span className="font-bold text-[#6B7280] block text-[10px] uppercase font-mono">
                TO:
              </span>
              <span className="text-[#1C1C1C]">Supervising Partner / Corporate Legal Team</span>
            </div>
            <div>
              <span className="font-bold text-[#6B7280] block text-[10px] uppercase font-mono">
                FROM:
              </span>
              <span className="text-[#1C1C1C]">First-Pass Triage (Legal Analyzer System)</span>
            </div>
            <div>
              <span className="font-bold text-[#6B7280] block text-[10px] uppercase font-mono">
                SUBJECT:
              </span>
              <span className="text-[#1C1C1C] font-semibold">
                Risk Analysis: Apex Data Solutions Master MSA
              </span>
            </div>
            <div>
              <span className="font-bold text-[#6B7280] block text-[10px] uppercase font-mono">
                TRIAGE STATUS:
              </span>
              <span className="text-[#991B1B] font-semibold">Redline Revisions Required</span>
            </div>
          </div>
        </div>

        {/* 1. Executive Summary */}
        <div className="space-y-2">
          <h4 className="font-serif font-bold text-sm text-[#0D1B2A]">1. Executive Summary</h4>
          <p className="text-xs sm:text-[13px] text-[#374151] leading-relaxed">
            This triage report reviews the incoming vendor Master Services Agreement submitted by
            Apex Data Solutions. The agreement contains four flagged provisions warranting partner
            review: uncapped third-party indemnification obligations, asymmetrical termination for
            convenience, indefinite confidentiality survival, and non-solicitation restrictions.
          </p>
        </div>

        {/* 2. Flagged Provisions & Exposure Audit */}
        <div className="space-y-3">
          <h4 className="font-serif font-bold text-sm text-[#0D1B2A]">
            2. Flagged Provisions &amp; Exposure Audit
          </h4>

          <div className="overflow-x-auto border border-[#E5E5E0]">
            <table className="w-full text-left text-xs font-sans">
              <thead>
                <tr className="border-b border-[#E5E5E0] bg-[#FAF9F5] text-[9px] font-mono uppercase tracking-wider text-[#6B7280]">
                  <th className="py-2 px-3 font-semibold">CLAUSE REF</th>
                  <th className="py-2 px-3 font-semibold">IDENTIFIED ISSUE</th>
                  <th className="py-2 px-3 font-semibold">SEVERITY</th>
                  <th className="py-2 px-3 font-semibold text-right">SCORE IMPACT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E0]">
                {MEMO_PROVISIONS.map((item) => (
                  <tr key={item.clauseRef} className="hover:bg-[#FAF9F5]">
                    <td className="py-2.5 px-3 font-mono font-semibold text-[#1C1C1C]">
                      {item.clauseRef}
                    </td>
                    <td className="py-2.5 px-3 text-[#1C1C1C] font-serif">{item.issue}</td>
                    <td className="py-2.5 px-3 font-mono text-[10px] font-bold">
                      <span className={item.severityColor}>{item.severity}</span>
                    </td>
                    <td className={`py-2.5 px-3 font-mono text-right font-semibold ${item.impactColor}`}>
                      {item.scoreImpact}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 3. Suggested Redlines */}
        <div className="space-y-1">
          <h4 className="font-serif font-bold text-sm text-[#0D1B2A]">
            3. Suggested redlines and negotiation recommendations
          </h4>
          <p className="text-xs text-[#6B7280] italic">
            [Suggested redline revisions and compromise positions — Illustrative example]
          </p>
        </div>

        {/* 4. Legal Citations */}
        <div className="space-y-1">
          <h4 className="font-serif font-bold text-sm text-[#0D1B2A]">
            4. Legal citations and precedents
          </h4>
          <p className="text-xs text-[#6B7280] italic">
            [Relevant governing jurisdiction precedents and reference citations — Illustrative
            example]
          </p>
        </div>

        {/* Bottom Triage Benchmark Rating Box */}
        <div className="pt-6 border-t border-[#E5E5E0] flex flex-col sm:flex-row items-center justify-between gap-4 font-sans">
          <div className="text-xs text-[#6B7280] font-mono">
            <span>Triage Benchmark: </span>
            <span className="font-bold text-[#1C1C1C]">Document score: 60 / 100</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#6B7280] block">
              Safety Rating
            </span>
            <span className="text-sm font-mono font-bold text-[#991B1B]">
              60 / 100 <span className="text-xs font-normal text-[#991B1B]">(Action Required)</span>
            </span>
          </div>
        </div>

        {/* Footer Reference */}
        <div className="pt-3 border-t border-[#F0F2F5] flex justify-between items-center text-[9px] font-mono text-[#9CA3AF] uppercase">
          <span>LEGAL ANALYZER MEMO REF: LA-2024-MSA</span>
          <span>Reference citations applied</span>
        </div>
      </div>

      {/* Action Link under Memo */}
      <div className="text-center pt-2">
        <Link
          href="/reports/1"
          className="text-xs font-mono font-semibold text-[#0D1B2A] hover:underline underline-offset-4 uppercase tracking-wider inline-flex items-center gap-1.5"
        >
          Download sample memo &rarr;
        </Link>
      </div>
    </section>
  );
}

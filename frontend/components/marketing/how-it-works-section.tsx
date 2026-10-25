/**
 * @file how-it-works-section.tsx
 * @description Renders Image 4: The 4-step linear triage process (01 Upload, 02 Extract, 03 Score, 04 Review)
 * and the "Clause audit & risk scoring" side-by-side section with the formal scoring table.
 */

import React from "react";

const PROCESS_STEPS = [
  {
    step: "01",
    title: "Upload a contract",
    description:
      "Add an NDA, SaaS agreement or employment contract. PDF, Word and text files are supported.",
  },
  {
    step: "02",
    title: "Clauses are extracted",
    description:
      "Every section, obligation, warranty, and definition is isolated and cataloged in order.",
  },
  {
    step: "03",
    title: "Risk is scored",
    description:
      "Deviations from standard playbooks and accepted norms receive numeric risk weights.",
  },
  {
    step: "04",
    title: "A person reviews and exports a memo",
    description:
      "Counsel validates the recommendations and exports the memo as PDF or Word.",
  },
];

const AUDIT_TABLE_ROWS = [
  {
    clauseRef: "11.2",
    title: "Indemnification and third-party claims",
    subtitle: "Unilateral, uncapped customer defense",
    severity: "HIGH",
    severityColor: "text-[#991B1B]",
    bulletColor: "bg-[#991B1B]",
    scoreImpact: "-15 points",
    impactColor: "text-[#991B1B]",
  },
  {
    clauseRef: "8.3",
    title: "Termination for convenience",
    subtitle: "One-sided vendor cancellation right on 30 days",
    severity: "HIGH",
    severityColor: "text-[#991B1B]",
    bulletColor: "bg-[#991B1B]",
    scoreImpact: "-15 points",
    impactColor: "text-[#991B1B]",
  },
  {
    clauseRef: "12.4",
    title: "Confidentiality term and survival",
    subtitle: "Indefinite duration without trade secret limit",
    severity: "MEDIUM",
    severityColor: "text-[#854D0E]",
    bulletColor: "bg-[#854D0E]",
    scoreImpact: "-5 points",
    impactColor: "text-[#854D0E]",
  },
  {
    clauseRef: "13.1",
    title: "Non-solicitation of personnel",
    subtitle: "Restricts general hiring: 24-month horizon",
    severity: "MEDIUM",
    severityColor: "text-[#854D0E]",
    bulletColor: "bg-[#854D0E]",
    scoreImpact: "-5 points",
    impactColor: "text-[#854D0E]",
  },
  {
    clauseRef: "16.2",
    title: "Governing law and severability",
    subtitle: "Standard Delaware choice of law and venue",
    severity: "LOW",
    severityColor: "text-[#166534]",
    bulletColor: "bg-[#166534]",
    scoreImpact: "None",
    impactColor: "text-[#6B7280]",
  },
];

export function HowItWorksSection() {
  return (
    <section className="w-full max-w-5xl mx-auto py-16 sm:py-24 border-t border-[#E5E5E0] space-y-16 sm:space-y-24">
      {/* ------------------------------------------------------------- */}
      {/* PART 1: 4-Step Process Grid                                    */}
      {/* ------------------------------------------------------------- */}
      <div className="space-y-12">
        <h2 className="font-serif text-3xl sm:text-4xl text-[#0D1B2A] tracking-tight">
          How it works
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
          {PROCESS_STEPS.map((item) => (
            <div key={item.step} className="space-y-3">
              <span className="font-mono text-2xl font-bold text-[#8C7A5B] block">
                {item.step}
              </span>
              <h3 className="font-serif font-bold text-base text-[#0D1B2A] leading-snug">
                {item.title}
              </h3>
              <p className="text-xs text-[#595959] leading-relaxed font-sans">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* PART 2: Clause audit & risk scoring (2-column layout + table)  */}
      {/* ------------------------------------------------------------- */}
      <div className="bg-white border border-[#E5E5E0] p-6 sm:p-10 shadow-xs">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Heading & Description */}
          <div className="lg:col-span-5 space-y-3">
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#6B7280] block">
              CLAUSE AUDIT
            </span>
            <h3 className="font-serif text-2xl sm:text-3xl text-[#0D1B2A] font-normal leading-tight">
              Clause audit &amp; risk scoring
            </h3>
            <p className="text-xs sm:text-[13px] text-[#595959] leading-relaxed font-sans pt-2">
              Identify key provisions in NDAs, SaaS terms and employment agreements. Get numerical
              safety scores calibrated against standard templates.
            </p>
          </div>

          {/* Right Column: Scored Table */}
          <div className="lg:col-span-7 space-y-3">
            <div className="overflow-x-auto border border-[#E5E5E0]">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#E5E5E0] bg-[#FAF9F5] text-[9px] font-mono uppercase tracking-wider text-[#6B7280]">
                    <th className="py-2.5 px-4 font-semibold">PROVISION</th>
                    <th className="py-2.5 px-4 font-semibold">SEVERITY</th>
                    <th className="py-2.5 px-4 font-semibold text-right">SCORE IMPACT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E0] font-sans">
                  {AUDIT_TABLE_ROWS.map((row) => (
                    <tr key={row.clauseRef} className="hover:bg-[#FAF9F5] transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-serif font-bold text-xs text-[#0D1B2A]">
                          {row.clauseRef} {row.title}
                        </div>
                        <div className="text-[11px] text-[#6B7280] font-sans mt-0.5">
                          {row.subtitle}
                        </div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`text-[10px] font-mono font-bold uppercase tracking-wider flex items-center gap-1.5 ${row.severityColor}`}
                        >
                          <span className={`w-1.5 h-1.5 ${row.bulletColor}`} />
                          {row.severity}
                        </span>
                      </td>
                      <td className={`py-3 px-4 text-right font-mono text-xs font-semibold ${row.impactColor}`}>
                        {row.scoreImpact}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table Footnote */}
            <p className="text-[11px] text-[#6B7280] font-mono leading-relaxed pt-1">
              Document score = 100, minus 15 for each High clause and 5 for each Medium clause.
              Range 0 to 100.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

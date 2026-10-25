/**
 * @file trust-and-faq-section.tsx
 * @description Renders Image 3: The dark "Human Review" trust section (Ink Navy #0D1B2A)
 * highlighting attorney oversight, followed by the Frequently Asked Questions accordion.
 */

"use client";

import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

const FAQ_ITEMS = [
  {
    question: "Does it replace a lawyer?",
    answer: "No. It provides first-pass analysis and does not replace review by a qualified lawyer.",
  },
  {
    question: "Which documents are supported?",
    answer:
      "NDAs, SaaS terms and employment agreements. Upload PDF, Word or text files up to 10 MB.",
  },
  {
    question: "How is the score calculated?",
    answer:
      "Each document starts at 100. Each High-risk clause deducts 15 points and each Medium-risk clause deducts 5. The score stays between 0 and 100.",
  },
  {
    question: "What happens to my files?",
    answer:
      "Files are processed in ephemeral memory for text extraction and risk scoring. They are stored in an isolated Supabase project with encryption at rest, and can be purged immediately by the document owner at any time.",
  },
];

export function TrustAndFaqSection() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const toggle = (idx: number) => {
    setOpenIdx(openIdx === idx ? null : idx);
  };

  return (
    <div className="w-full">
      {/* ------------------------------------------------------------- */}
      {/* PART 1: Dark Trust Section (Ink Navy #0D1B2A)                  */}
      {/* ------------------------------------------------------------- */}
      <section className="w-full bg-[#0D1B2A] text-white py-16 sm:py-24 px-6 sm:px-8 md:px-12">
        <div className="max-w-5xl mx-auto space-y-12">
          {/* Section Eyebrow & Title */}
          <div className="space-y-4 max-w-3xl">
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#D4AF37] block">
              HUMAN REVIEW
            </span>
            <h2 className="font-serif text-3xl sm:text-4xl text-[#FAF9F5] leading-tight font-normal">
              Flagged clauses wait in a review queue. The analysis assists; a lawyer decides.
            </h2>
            <p className="text-xs sm:text-sm text-[#A0AEC0] leading-relaxed font-sans pt-2">
              Our machine triage never executes autonomous contract modifications or unilateral
              approvals. Every extracted violation and scored risk item is positioned directly in a
              lawyer&apos;s docket, paired with standard clauses and recommendations for informed
              attorney oversight.
            </p>
          </div>

          {/* 3 Value Columns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-6 border-t border-[#1E2D42]">
            <div className="space-y-2">
              <h3 className="font-serif font-bold text-sm text-[#FAF9F5]">
                01 Assistive model
              </h3>
              <p className="text-xs text-[#8A9BA8] leading-relaxed font-sans">
                Surface anomalies without overriding professional discretion.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="font-serif font-bold text-sm text-[#FAF9F5]">
                02 Export: Download the memo as PDF or Word.
              </h3>
              <p className="text-xs text-[#8A9BA8] leading-relaxed font-sans">
                Export formatted memos directly to team members.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="font-serif font-bold text-sm text-[#FAF9F5]">
                03 Side-by-side view: Flagged clauses are shown beside the contract text.
              </h3>
              <p className="text-xs text-[#8A9BA8] leading-relaxed font-sans">
                Inspect exact clause language with alongside analysis.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* PART 2: Frequently Asked Questions (Paper #F9F6F0 background)  */}
      {/* ------------------------------------------------------------- */}
      <section className="w-full max-w-5xl mx-auto py-16 sm:py-24 px-6 sm:px-8 space-y-10 text-left">
        <div className="space-y-3">
          <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#6B7280] block">
            QUESTIONS
          </span>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#0D1B2A] tracking-tight">
            Frequently asked questions
          </h2>
        </div>

        {/* FAQ Accordion List */}
        <div className="divide-y divide-[#E5E5E0] border-t border-b border-[#E5E5E0]">
          {FAQ_ITEMS.map((item, idx) => (
            <div key={idx} className="py-5 transition-colors">
              <button
                type="button"
                onClick={() => toggle(idx)}
                className="w-full flex items-center justify-between text-left group cursor-pointer focus:outline-none"
              >
                <span className="font-serif font-medium text-base sm:text-lg text-[#0D1B2A] group-hover:text-[#8C7A5B] transition-colors">
                  {item.question}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-[#6B7280] transition-transform duration-200 shrink-0 ml-4 ${
                    openIdx === idx ? "transform rotate-180" : ""
                  }`}
                />
              </button>

              {/* Collapsible Answer */}
              {openIdx === idx ? (
                <div className="pt-3 text-xs sm:text-[13px] text-[#595959] leading-relaxed font-sans max-w-3xl">
                  {item.answer}
                </div>
              ) : (
                <div className="pt-2 text-xs text-[#595959] leading-relaxed font-sans max-w-3xl">
                  {item.answer}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

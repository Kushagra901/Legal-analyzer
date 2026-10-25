/**
 * @file footer-cta-section.tsx
 * @description Final call-to-action banner ("Start with one contract") and comprehensive
 * legal application footer with mandatory disclaimer, navigation links, and copyright.
 */

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function FooterCtaSection() {
  return (
    <div className="w-full">
      {/* ------------------------------------------------------------- */}
      {/* Final Call to Action Section                                   */}
      {/* ------------------------------------------------------------- */}
      <section className="w-full max-w-5xl mx-auto py-16 sm:py-24 px-6 sm:px-8 text-center border-t border-[#E5E5E0] space-y-6">
        <h2 className="font-serif text-3xl sm:text-4xl text-[#0D1B2A] tracking-tight">
          Start with one contract.
        </h2>
        <p className="text-xs sm:text-sm text-[#595959] leading-relaxed font-sans max-w-md mx-auto">
          Upload an NDA, SaaS agreement, or employment contract to see the clause audit and risk
          score in seconds.
        </p>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/signup">
            <Button variant="primary" className="px-8 py-3 text-xs min-w-[200px]">
              Analyze a contract
            </Button>
          </Link>
          <Link
            href="/reports/1"
            className="text-xs font-mono font-semibold text-[#0D1B2A] hover:underline underline-offset-4 uppercase tracking-wider"
          >
            See a sample memo &rarr;
          </Link>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* Footer                                                        */}
      {/* ------------------------------------------------------------- */}
      <footer className="w-full border-t border-[#E5E5E0] bg-white py-12 px-6 sm:px-8 md:px-12 text-[#6B7280]">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
            <span className="font-serif text-lg font-bold tracking-tight text-[#0D1B2A]">
              LEGAL ANALYZER
            </span>
            <div className="flex flex-wrap gap-6 text-xs font-sans">
              <Link href="/login" className="hover:text-[#0D1B2A] transition-colors">
                Sign In
              </Link>
              <Link href="/signup" className="hover:text-[#0D1B2A] transition-colors">
                Sign Up
              </Link>
              <Link href="/dashboard" className="hover:text-[#0D1B2A] transition-colors">
                Dashboard
              </Link>
              <Link href="/review" className="hover:text-[#0D1B2A] transition-colors">
                Review Queue
              </Link>
            </div>
          </div>

          <div className="border-t border-[#F0F2F5] pt-6 space-y-3 text-[11px] leading-relaxed">
            <p>
              <strong className="text-[#1C1C1C]">Disclaimer:</strong> Legal Analyzer provides
              automated analysis to assist in contract triage. It does not provide licensed legal
              advice and does not replace review by a qualified lawyer.
            </p>
            <p className="font-mono text-[10px] text-[#9CA3AF]">
              &copy; 2026 Legal Analyzer. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

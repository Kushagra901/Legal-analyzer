/**
 * @file page.tsx
 * @description Branded landing page for the Legal Analyzer application.
 */

import React from "react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] flex flex-col justify-between font-sans">
      {/* Header Navigation */}
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <span className="font-serif text-xl font-normal text-[#0d1b2a]">
          Legal Analyzer
        </span>
        <div className="flex items-center space-x-6">
          <Link
            href="/login"
            className="text-xs font-semibold text-[#5c5b57] hover:text-[#0d1b2a] uppercase tracking-wider transition-colors duration-150"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] px-4 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors duration-200"
          >
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero / Main Marketing Section */}
      <main className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto text-center space-y-8">
        <div className="space-y-4">
          <span className="inline-block bg-[#0d1b2a]/10 text-[#0d1b2a] border border-[#0d1b2a]/20 px-3 py-1 text-[10px] font-bold uppercase tracking-widest">
            AI-Assisted Contract Triage
          </span>
          <h1 className="font-serif text-4xl sm:text-5xl font-normal text-[#0d1b2a] tracking-tight leading-tight max-w-2xl mx-auto">
            Review contracts before sending them to your lawyer.
          </h1>
          <p className="text-sm sm:text-base text-[#5c5b57] leading-relaxed max-w-xl mx-auto">
            Extract clauses, detect one-sided terms, flag liability exposures, and compile exportable audit reports in seconds.
          </p>
        </div>

        {/* Feature Cards Grid (Flat Surfaces) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full text-left mt-8">
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none">
            <h3 className="font-serif text-lg text-[#0d1b2a] mb-2">Clause Audit & Risk Scoring</h3>
            <p className="text-xs text-[#5c5b57] leading-relaxed">
              Identify key provisions in NDAs, SaaS Terms, and Consulting Agreements. Get numerical safety scores calibrated against standard templates.
            </p>
          </div>
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none">
            <h3 className="font-serif text-lg text-[#0d1b2a] mb-2">Plain-English Summaries</h3>
            <p className="text-xs text-[#5c5b57] leading-relaxed">
              Skip complex legal jargon. Our models break down legal terms into clear, actionable advice highlighting what you should negotiate.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/signup"
            className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] px-8 py-3 text-xs font-semibold uppercase tracking-wider transition-colors duration-200 text-center min-w-[200px]"
          >
            Create Free Account
          </Link>
          <Link
            href="/login"
            className="border border-[#0d1b2a] text-[#0d1b2a] hover:bg-[#0d1b2a] hover:text-[#faf9f6] px-8 py-3 text-xs font-semibold uppercase tracking-wider transition-colors duration-200 text-center min-w-[200px]"
          >
            Sign In to Dashboard
          </Link>
        </div>
      </main>

      {/* Disclaimer / Footer */}
      <footer className="border-t border-[#e0dfdb] bg-white px-8 py-8 text-center text-[10px] text-[#8a8985] leading-relaxed">
        <div className="max-w-4xl mx-auto space-y-2">
          <p>
            <strong>Disclaimer:</strong> Legal Analyzer provides automated analysis to assist in contract triage. It does not provide legal advice and does not replace a licensed lawyer.
          </p>
          <p className="text-[9px]">
            &copy; {new Date().getFullYear()} Legal Analyzer. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

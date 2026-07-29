/**
 * @file page.tsx
 * @description Branded landing page for the Legal Analyzer application.
 */

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--bg-page)] text-[var(--text-main)] flex flex-col justify-between font-sans">
      {/* Header Navigation */}
      <header className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-8 py-4 flex justify-between items-center">
        <span className="font-serif text-xl font-bold tracking-tight text-[var(--accent-primary)]">
          LEGAL ANALYZER
        </span>
        <div className="flex items-center space-x-6">
          <Link
            href="/login"
            className="text-xs font-semibold text-[var(--text-muted)] hover:text-[var(--text-main)] uppercase tracking-wider transition-colors duration-150"
          >
            Sign In
          </Link>
          <Link href="/signup">
            <Button variant="primary">Get Started</Button>
          </Link>
        </div>
      </header>

      {/* Hero / Main Marketing Section */}
      <main className="flex-1 flex flex-col items-center justify-center p-8 max-w-4xl mx-auto text-center space-y-8">
        <div className="space-y-4">
          <span className="inline-block bg-[var(--bg-surface)] text-[var(--accent-primary)] border border-[var(--border-subtle)] px-3 py-1 text-[10px] font-bold uppercase tracking-widest">
            AI-Assisted Contract Triage
          </span>
          <h1 className="font-serif text-4xl sm:text-5xl font-normal text-[var(--accent-primary)] tracking-tight leading-tight max-w-2xl mx-auto">
            First-pass contract intelligence before partner review.
          </h1>
          <p className="text-sm sm:text-base text-[var(--text-muted)] leading-relaxed max-w-xl mx-auto">
            Extract clauses, detect one-sided terms, flag liability exposures, and compile publication-ready memo reports.
          </p>
        </div>

        {/* Feature Cards Grid (Flat Surfaces) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full text-left mt-8">
          <div className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-none">
            <h3 className="font-serif text-lg text-[var(--accent-primary)] font-bold mb-2">
              Clause Audit & Risk Scoring
            </h3>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Identify key provisions in NDAs, SaaS Terms, and Employment Agreements. Get numerical safety scores calibrated against standard templates.
            </p>
          </div>
          <div className="border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 rounded-none">
            <h3 className="font-serif text-lg text-[var(--accent-primary)] font-bold mb-2">
              Interactive Split-Pane Results
            </h3>
            <p className="text-xs text-[var(--text-muted)] leading-relaxed">
              Inspect original contract text alongside parsed clauses, risk severity indicators, statutory citations, and NDA compliance violations.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/signup">
            <Button variant="primary" className="px-8 py-3 text-xs min-w-[200px]">
              Create Account
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="outline" className="px-8 py-3 text-xs min-w-[200px]">
              Access Workspace
            </Button>
          </Link>
        </div>
      </main>

      {/* Disclaimer / Footer */}
      <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-8 py-8 text-center text-[11px] text-[var(--text-muted)] leading-relaxed">
        <div className="max-w-4xl mx-auto space-y-2">
          <p>
            <strong>Disclaimer:</strong> Legal Analyzer provides automated analysis to assist in contract triage. It does not provide licensed legal advice and does not replace review by a qualified lawyer.
          </p>
        </div>
      </footer>
    </div>
  );
}

/**
 * @file page.tsx
 * @description Master landing page for Legal Analyzer completely overhauled to match
 * the 6 reference design images.
 * Structured into 6 distinct sections:
 * 1. Hero Section (Headline + Master Services Agreement split-pane mockup)
 * 2. How It Works (01-04 steps + Clause audit & risk scoring table)
 * 3. Interactive Split-Pane Results (Dual-pane analysis + 3-column redlines card)
 * 4. Sample Memo (Formal printed memorandum sheet)
 * 5. Trust & FAQ (Dark human review banner + FAQ accordion)
 * 6. Footer & Final CTA ("Start with one contract" + Disclaimer footer)
 */

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { HeroMockup } from "@/components/marketing/hero-mockup";
import { HowItWorksSection } from "@/components/marketing/how-it-works-section";
import { ResultsSection } from "@/components/marketing/results-section";
import { SampleMemoSection } from "@/components/marketing/sample-memo-section";
import { TrustAndFaqSection } from "@/components/marketing/trust-and-faq-section";
import { FooterCtaSection } from "@/components/marketing/footer-cta-section";

export default function MarketingPage() {
  return (
    <div className="min-h-screen bg-[#F9F6F0] text-[#1C1C1C] flex flex-col font-sans selection:bg-[#E5E5E0]">
      {/* ------------------------------------------------------------- */}
      {/* Top Header Navigation                                          */}
      {/* ------------------------------------------------------------- */}
      <header className="w-full border-b border-[#E5E5E0] bg-[#F9F6F0] px-6 sm:px-10 py-4 flex justify-between items-center sticky top-0 z-50">
        <Link href="/" className="font-serif text-lg sm:text-xl font-bold tracking-tight text-[#0D1B2A]">
          LEGAL ANALYZER
        </Link>
        <div className="flex items-center space-x-6 sm:space-x-8">
          <Link
            href="/login"
            className="text-xs font-semibold text-[#595959] hover:text-[#0D1B2A] transition-colors"
          >
            Sign in
          </Link>
          <Link href="/signup">
            <Button
              variant="primary"
              className="bg-[#0D1B2A] text-white hover:bg-[#1A2F4C] border-[#0D1B2A] text-xs font-semibold px-4 py-2 uppercase tracking-wider"
            >
              Get started
            </Button>
          </Link>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* MAIN CONTENT                                                  */}
      {/* ------------------------------------------------------------- */}
      <main className="flex-1 flex flex-col items-center">
        {/* ----------------------------------------------------------- */}
        {/* 1. HERO SECTION (Image 1)                                   */}
        {/* ----------------------------------------------------------- */}
        <section className="w-full max-w-5xl mx-auto px-6 sm:px-8 pt-12 sm:pt-20 pb-12 sm:pb-16 text-center space-y-6">
          {/* Eyebrow tag */}
          <div className="flex justify-center">
            <span className="inline-block bg-[#F9F6F0] text-[#0D1B2A] border border-[#E5E5E0] px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-widest">
              AI-ASSISTED CONTRACT TRIAGE
            </span>
          </div>

          {/* Headline */}
          <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl font-normal text-[#0D1B2A] tracking-tight leading-[1.12] max-w-3xl mx-auto">
            First-pass contract intelligence before partner review.
          </h1>

          {/* Subtext */}
          <p className="text-xs sm:text-sm md:text-base text-[#595959] leading-relaxed max-w-2xl mx-auto font-sans">
            Extract clauses, detect one-sided terms, flag liability exposures, and compile
            publication-ready memo reports.
          </p>

          {/* CTAs */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <Button
                variant="primary"
                className="bg-[#0D1B2A] hover:bg-[#1A2F4C] border-[#0D1B2A] text-white px-7 py-3 text-xs font-semibold uppercase tracking-wider min-w-[190px]"
              >
                Analyze a contract
              </Button>
            </Link>
            <Link
              href="/reports/1"
              className="text-xs font-mono font-semibold text-[#0D1B2A] hover:underline underline-offset-4 tracking-wider uppercase inline-flex items-center gap-1.5"
            >
              See a sample memo &rarr;
            </Link>
          </div>

          {/* Large Interactive Split-Pane Product Mockup */}
          <div className="pt-8 sm:pt-12">
            <HeroMockup />
          </div>
        </section>

        {/* ----------------------------------------------------------- */}
        {/* 2. HOW IT WORKS & CLAUSE AUDIT (Image 4)                    */}
        {/* ----------------------------------------------------------- */}
        <div className="w-full px-6 sm:px-8">
          <HowItWorksSection />
        </div>

        {/* ----------------------------------------------------------- */}
        {/* 3. INTERACTIVE SPLIT-PANE RESULTS & REDLINES (Image 5)      */}
        {/* ----------------------------------------------------------- */}
        <div className="w-full px-6 sm:px-8">
          <ResultsSection />
        </div>

        {/* ----------------------------------------------------------- */}
        {/* 4. SAMPLE MEMO (Image 2)                                    */}
        {/* ----------------------------------------------------------- */}
        <div className="w-full px-6 sm:px-8">
          <SampleMemoSection />
        </div>

        {/* ----------------------------------------------------------- */}
        {/* 5. TRUST & FAQ (Image 3)                                    */}
        {/* ----------------------------------------------------------- */}
        <TrustAndFaqSection />

        {/* ----------------------------------------------------------- */}
        {/* 6. FINAL CTA & DISCLAIMER FOOTER                            */}
        {/* ----------------------------------------------------------- */}
        <FooterCtaSection />
      </main>
    </div>
  );
}

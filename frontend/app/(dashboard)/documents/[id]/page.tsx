/**
 * @file page.tsx
 * @description Document detail view page showing text analysis, clauses, and risk assessment.
 */

import React from "react";
import Link from "next/link";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function DocumentDetailPage({ params }: PageProps) {
  const resolvedParams = await params;
  const docId = resolvedParams.id;

  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
      {/* Header */}
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Link href="/dashboard" className="text-xs text-[#5c5b57] hover:underline uppercase tracking-wider font-semibold">
            &larr; Back
          </Link>
          <h1 className="font-serif text-xl font-normal text-[#0d1b2a]">Document: {docId}</h1>
        </div>
        <Link href={`/reports/${docId}`} className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] px-4 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors duration-200">
          View Report
        </Link>
      </header>

      {/* Main View Grid */}
      <main className="max-w-7xl mx-auto p-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left pane: Original text */}
        <section className="border border-[#e0dfdb] bg-white p-6 rounded-none flex flex-col h-[600px]">
          <h2 className="font-serif text-lg mb-4 text-[#0d1b2a]">Original Source Document</h2>
          <div className="flex-1 bg-[#faf9f6] p-4 font-mono text-[11px] leading-relaxed overflow-y-auto border border-[#e0dfdb] whitespace-pre-wrap select-text">
            {`MUTUAL NON-DISCLOSURE AGREEMENT

1. Purpose. The parties wish to explore a potential business relationship of mutual interest...

2. Confidential Information. "Confidential Information" means any information or materials disclosed...`}
          </div>
        </section>

        {/* Right pane: Extracted Clauses & Risk analysis */}
        <section className="space-y-6">
          {/* Overview Card */}
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-serif text-lg text-[#0d1b2a]">Risk Assessment</h3>
                <p className="text-xs text-[#5c5b57]">Confidence score: 98%</p>
              </div>
              <div className="text-right">
                <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded-none uppercase tracking-wider">
                  Low Risk
                </span>
                <p className="text-lg font-mono font-bold text-[#0d1b2a] mt-1">92% score</p>
              </div>
            </div>
            <p className="text-xs text-[#5c5b57] leading-relaxed">
              Standard mutual agreement. All obligations of confidentiality are reciprocal and conform to general commercial standards. Minimal legal exposure detected.
            </p>
          </div>

          {/* List of Clauses */}
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none space-y-4">
            <h3 className="font-serif text-lg text-[#0d1b2a] border-b border-[#e0dfdb] pb-2">Identified Clauses</h3>
            
            <div className="p-4 border border-[#e0dfdb] bg-[#faf9f6]">
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#0d1b2a]">Confidentiality obligations</h4>
                <span className="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-0.5 uppercase">Low</span>
              </div>
              <p className="text-xs text-[#5c5b57] leading-relaxed">
                The Receiving Party agrees: (a) to hold the Disclosing Party&apos;s Confidential Information in strict confidence...
              </p>
            </div>

            <div className="p-4 border border-[#e0dfdb] bg-[#faf9f6]">
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[#0d1b2a]">Limitation of Liability</h4>
                <span className="bg-green-100 text-green-800 text-[10px] font-bold px-2 py-0.5 uppercase">Low</span>
              </div>
              <p className="text-xs text-[#5c5b57] leading-relaxed">
                NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES...
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-[#e0dfdb] text-[11px] text-[#8a8985]">
        <strong>Disclaimer:</strong> Legal Analyzer is an automated system. Always verify outputs with legal counsel before executing.
      </footer>
    </div>
  );
}


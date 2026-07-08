/**
 * @file page.tsx
 * @description Dashboard home page displaying lists of documents, overall status, and action controls.
 */

import React from "react";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
      {/* Top Header */}
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <h1 className="font-serif text-2xl font-normal text-[#0d1b2a]">
          Legal Analyzer
        </h1>
        <div className="flex items-center space-x-4">
          <span className="text-xs text-[#5c5b57]">Welcome, User</span>
          <Link href="/login" className="text-xs font-semibold text-[#0d1b2a] uppercase tracking-wider hover:underline">
            Sign Out
          </Link>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="max-w-7xl mx-auto p-8 space-y-8">
        {/* Welcome Section */}
        <section className="border border-[#e0dfdb] bg-white p-8 rounded-none">
          <h2 className="font-serif text-2xl mb-2 text-[#0d1b2a]">Document Triage Dashboard</h2>
          <p className="text-sm text-[#5c5b57] max-w-2xl">
            Upload new legal documents (contracts, NDAs, SaaS agreements) for AI-assisted first-pass review. Highlight clauses, flag risk vectors, and compile compliance audit reports.
          </p>
        </section>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Upload Widget */}
          <div className="md:col-span-1 border border-[#e0dfdb] bg-white p-6 rounded-none flex flex-col justify-between min-h-[300px]">
            <div>
              <h3 className="font-serif text-lg mb-3 text-[#0d1b2a]">Analyze Document</h3>
              <p className="text-xs text-[#5c5b57] mb-4">
                Supported formats: PDF, TXT, DOCX. Max size 10MB.
              </p>
              <div className="border border-dashed border-[#e0dfdb] bg-[#faf9f6] h-32 flex flex-col items-center justify-center text-[#5c5b57] text-xs p-4">
                <span>Drag & drop file here</span>
                <span className="text-[10px] text-gray-400 mt-1">or click to browse</span>
              </div>
            </div>
            <button className="w-full bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] py-2 text-xs font-semibold uppercase tracking-wider rounded-none transition-colors duration-200 mt-4">
              Upload file
            </button>
          </div>

          {/* Document List Table */}
          <div className="md:col-span-2 border border-[#e0dfdb] bg-white p-6 rounded-none">
            <h3 className="font-serif text-lg mb-4 text-[#0d1b2a]">Recent Documents</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#e0dfdb] text-[#5c5b57] uppercase tracking-wider font-semibold">
                    <th className="py-2.5">Filename</th>
                    <th className="py-2.5">Date</th>
                    <th className="py-2.5">Risk Level</th>
                    <th className="py-2.5 text-right">Score</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[#e0dfdb] hover:bg-[#faf9f6] cursor-pointer">
                    <td className="py-3 font-semibold text-[#0d1b2a]">
                      <Link href="/documents/doc_001">Mutual NDA - Apex Tech & Horizon.txt</Link>
                    </td>
                    <td className="py-3 text-[#5c5b57]">2025-10-12</td>
                    <td className="py-3">
                      <span className="bg-green-100 text-green-800 px-2 py-0.5 font-semibold">LOW</span>
                    </td>
                    <td className="py-3 text-right font-mono font-bold">92%</td>
                  </tr>
                  <tr className="border-b border-[#e0dfdb] hover:bg-[#faf9f6] cursor-pointer">
                    <td className="py-3 font-semibold text-[#0d1b2a]">
                      <Link href="/documents/doc_002">Enterprise SaaS Terms - CloudScale.txt</Link>
                    </td>
                    <td className="py-3 text-[#5c5b57]">2025-08-24</td>
                    <td className="py-3">
                      <span className="bg-red-100 text-red-800 px-2 py-0.5 font-semibold">HIGH</span>
                    </td>
                    <td className="py-3 text-right font-mono font-bold text-red-700">35%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Disclaimers Footer */}
      <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-[#e0dfdb] text-[11px] text-[#8a8985] leading-relaxed">
        <strong>Disclaimer:</strong> Legal Analyzer is an automated system powered by AI. It provides a first-pass triage review and does not constitute formal legal advice. Always review generated logs and reports with a licensed professional before execution.
      </footer>
    </div>
  );
}


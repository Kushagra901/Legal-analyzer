/**
 * @file page.tsx
 * @description Admin page for system audits, logging, and pipeline monitor dashboard.
 */

import React from "react";

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <a href="/dashboard" className="text-xs text-[#5c5b57] hover:underline uppercase tracking-wider font-semibold">
            &larr; Dashboard
          </a>
          <h1 className="font-serif text-xl font-normal text-[#0d1b2a]">System Administration</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-8 space-y-8">
        <section className="border border-[#e0dfdb] bg-white p-6 rounded-none">
          <h2 className="font-serif text-lg text-[#0d1b2a] mb-2">Audit Logs</h2>
          <p className="text-xs text-[#5c5b57] mb-6">
            Review history logs, uploads, and critical administrative activities on documents.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#e0dfdb] text-[#5c5b57] uppercase tracking-wider font-semibold">
                  <th className="py-2">Log ID</th>
                  <th className="py-2">Action</th>
                  <th className="py-2">Document ID</th>
                  <th className="py-2">User</th>
                  <th className="py-2 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#e0dfdb] hover:bg-[#faf9f6]">
                  <td className="py-3 font-mono">log_01239</td>
                  <td className="py-3 font-semibold text-green-700">UPLOAD_DOCUMENT</td>
                  <td className="py-3 font-mono">doc_001</td>
                  <td className="py-3">kushal@company.com</td>
                  <td className="py-3 text-right">2026-07-08 11:39:00</td>
                </tr>
                <tr className="border-b border-[#e0dfdb] hover:bg-[#faf9f6]">
                  <td className="py-3 font-mono">log_01240</td>
                  <td className="py-3 font-semibold text-blue-700">GENERATE_REPORT</td>
                  <td className="py-3 font-mono">doc_001</td>
                  <td className="py-3">kushal@company.com</td>
                  <td className="py-3 text-right">2026-07-08 11:42:00</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

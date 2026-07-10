"use client";

/**
 * @file page.tsx
 * @description Dashboard home page displaying lists of documents, overall status, and action controls.
 */

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { apiClient } from "@/lib/api";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";

interface DocumentItem {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at: string;
}

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.fetchDocuments();
      setDocuments(data);
      setErrorMessage(null);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load documents. Please check backend connection.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUploadSuccess = () => {
    loadDocuments();
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      return dateStr.split("T")[0];
    } catch {
      return dateStr;
    }
  };

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
              <UploadDropzone onUploadSuccess={handleUploadSuccess} />
            </div>
          </div>

          {/* Document List Table */}
          <div className="md:col-span-2 border border-[#e0dfdb] bg-white p-6 rounded-none">
            <h3 className="font-serif text-lg mb-4 text-[#0d1b2a]">Recent Documents</h3>
            
            {errorMessage && (
              <div className="mb-4 p-3 bg-[#faf9f6] border border-[#ff4d4d] text-[#ff4d4d] text-xs flex items-center justify-between">
                <span>{errorMessage}</span>
                <button 
                  onClick={() => setErrorMessage(null)} 
                  className="text-xs font-bold hover:underline cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            )}

            {isLoading ? (
              <div className="space-y-4">
                {/* Skeletons styled like table rows */}
                <div className="border-b border-[#e0dfdb] pb-4 flex justify-between items-center animate-pulse">
                  <div className="h-4 bg-[#e0dfdb] w-1/3"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                </div>
                <div className="border-b border-[#e0dfdb] pb-4 flex justify-between items-center animate-pulse">
                  <div className="h-4 bg-[#e0dfdb] w-1/4"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                </div>
                <div className="border-b border-[#e0dfdb] pb-4 flex justify-between items-center animate-pulse">
                  <div className="h-4 bg-[#e0dfdb] w-1/2"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                  <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
                </div>
              </div>
            ) : documents.length === 0 ? (
              <EmptyState 
                title="No documents yet" 
                description="Upload a legal document on the left to start a first-pass review."
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="py-2.5">Filename</TableHead>
                    <TableHead className="py-2.5">Date</TableHead>
                    <TableHead className="py-2.5">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.document_id}>
                      <TableCell className="py-3 font-semibold text-[#0d1b2a]">
                        <Link href={`/documents/${doc.document_id}`} className="hover:underline">
                          {doc.filename}
                        </Link>
                      </TableCell>
                      <TableCell className="py-3 text-[#5c5b57]">
                        {formatDate(doc.uploaded_at)}
                      </TableCell>
                      <TableCell className="py-3">
                        <Badge variant={doc.status === "processing" ? "neutral" : "low"}>
                          {doc.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
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


"use client";

/**
 * @file page.tsx
 * @description Document detail view page showing text analysis, clauses, and risk assessment.
 */

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { apiClient } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

interface Clause {
  id: string;
  type: string;
  text: string;
  explanation: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
}

interface Citation {
  source: string;
  citation: string;
}

interface DocumentData {
  document_id: string;
  filename: string;
  status: string;
  uploaded_at: string;
  original_text: string;
  analysis: {
    safety_score: number;
    risk_level: string;
    summary: string;
    clauses: Clause[];
    citations: Citation[];
  };
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function DocumentDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const docId = resolvedParams.id;

  const router = useRouter();
  const [doc, setDoc] = useState<DocumentData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [selectedClauseText, setSelectedClauseText] = useState<string | null>(null);

  useEffect(() => {
    const checkSessionAndFetch = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.push("/login");
        return;
      }
      try {
        setIsLoading(true);
        const dataDoc = await apiClient.fetchDocument(docId);
        setDoc(dataDoc);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load document analysis details.");
      } finally {
        setIsLoading(false);
      }
    };
    checkSessionAndFetch();
  }, [docId, router]);

  useEffect(() => {
    if (selectedClauseText) {
      const element = document.getElementById("highlighted-clause");
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [selectedClauseText]);

  const getHighlightedText = (text: string, highlight: string | null) => {
    if (!text) return "";
    if (!highlight || !text.includes(highlight)) {
      return text;
    }
    const index = text.indexOf(highlight);
    const before = text.substring(0, index);
    const after = text.substring(index + highlight.length);
    return (
      <>
        {before}
        <mark id="highlighted-clause" className="bg-[#fff3cd] text-[#856404] px-1 py-0.5 font-semibold transition-all duration-150 border border-[#ffeeba]">
          {highlight}
        </mark>
        {after}
      </>
    );
  };

  const handleClauseClick = (clause: Clause) => {
    setSelectedClauseId(clause.id);
    setSelectedClauseText(clause.text);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
        <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
          <div className="h-6 bg-[#e0dfdb] w-1/4 animate-pulse"></div>
        </header>
        <main className="max-w-7xl mx-auto p-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="border border-[#e0dfdb] bg-white p-6 h-[600px] flex flex-col justify-between animate-pulse">
            <div className="h-6 bg-[#e0dfdb] w-1/3 mb-4"></div>
            <div className="flex-1 bg-[#faf9f6] border border-[#e0dfdb]"></div>
          </div>
          <div className="space-y-6 animate-pulse">
            <div className="border border-[#e0dfdb] bg-white p-6 h-40"></div>
            <div className="border border-[#e0dfdb] bg-white p-6 h-80"></div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans flex flex-col items-center justify-center p-8">
        <div className="max-w-md w-full border border-[#ff4d4d] bg-white p-6 text-center space-y-4">
          <h2 className="font-serif text-lg text-[#0d1b2a]">Analysis Error</h2>
          <p className="text-xs text-[#5c5b57]">{error || "Failed to load document analysis details."}</p>
          <Link href="/dashboard" className="inline-block bg-[#0d1b2a] text-white px-4 py-2 text-xs font-semibold uppercase tracking-wider hover:bg-[#1a2f4c]">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
      {/* Header */}
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Link href="/dashboard" className="text-xs text-[#5c5b57] hover:underline uppercase tracking-wider font-semibold">
            &larr; Back
          </Link>
          <h1 className="font-serif text-xl font-normal text-[#0d1b2a]">Document: {doc.filename}</h1>
        </div>
        <Link href={`/reports/${doc.document_id}`} className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] px-4 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors duration-200">
          View Report
        </Link>
      </header>

      {/* Main View Grid */}
      <main className="max-w-7xl mx-auto p-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left pane: Original text */}
        <section className="border border-[#e0dfdb] bg-white p-6 rounded-none flex flex-col h-[600px]">
          <h2 className="font-serif text-lg mb-4 text-[#0d1b2a]">Original Source Document</h2>
          <div className="flex-1 bg-[#faf9f6] p-6 font-mono text-[11px] leading-relaxed overflow-y-auto border border-[#e0dfdb] whitespace-pre-wrap select-text scroll-smooth">
            {getHighlightedText(doc.original_text, selectedClauseText)}
          </div>
        </section>

        {/* Right pane: Extracted Clauses & Risk analysis */}
        <section className="space-y-6 overflow-y-auto max-h-[600px] pr-2">
          {/* Overview Card */}
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-serif text-lg text-[#0d1b2a]">Risk Assessment</h3>
                <p className="text-xs text-[#5c5b57] mt-1">Confidence rating: high verification</p>
              </div>
              <div className="text-right">
                <Badge variant={doc.analysis.risk_level.toLowerCase() === "low" ? "low" : "high"}>
                  {doc.analysis.risk_level} Risk
                </Badge>
                <p className="text-lg font-mono font-bold text-[#0d1b2a] mt-1">{doc.analysis.safety_score}% score</p>
              </div>
            </div>
            <p className="text-xs text-[#5c5b57] leading-relaxed border-t border-[#e0dfdb] pt-4">
              {doc.analysis.summary}
            </p>
          </div>

          {/* List of Clauses */}
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none space-y-4">
            <h3 className="font-serif text-lg text-[#0d1b2a] border-b border-[#e0dfdb] pb-2">Identified Clauses</h3>
            <p className="text-[10px] text-[#8a8985] uppercase tracking-wider">Click a clause box to locate it in the source text.</p>

            <div className="space-y-3">
              {doc.analysis.clauses.map((clause) => (
                <div 
                  key={clause.id}
                  onClick={() => handleClauseClick(clause)}
                  className={`p-4 border cursor-pointer transition-all duration-150 rounded-none text-left
                    ${selectedClauseId === clause.id 
                      ? "border-[#0d1b2a] bg-[#faf9f6]" 
                      : "border-[#e0dfdb] bg-white hover:bg-[#faf9f6]"}`}
                >
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-[#0d1b2a]">{clause.type}</h4>
                    <Badge variant={clause.severity.toLowerCase() === "low" ? "low" : "high"}>
                      {clause.severity}
                    </Badge>
                  </div>
                  <p className="text-xs text-[#5c5b57] leading-relaxed line-clamp-3 mb-2 font-mono bg-[#faf9f6] p-2 border border-[#e0dfdb]">
                    {clause.text}
                  </p>
                  <p className="text-[11px] text-[#8a8985] italic leading-normal">
                    {clause.explanation}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Citations list */}
          <div className="border border-[#e0dfdb] bg-white p-6 rounded-none space-y-4">
            <h3 className="font-serif text-lg text-[#0d1b2a] border-b border-[#e0dfdb] pb-2">Governing Citations</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="py-2">Legal Source</TableHead>
                  <TableHead className="py-2">Context</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {doc.analysis.citations.map((cite, index) => (
                  <TableRow key={index}>
                    <TableCell className="py-2.5 font-semibold text-[#0d1b2a]">{cite.source}</TableCell>
                    <TableCell className="py-2.5 text-[#5c5b57]">{cite.citation}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      </main>

      <footer className="max-w-7xl mx-auto px-8 py-12 border-t border-[#e0dfdb] text-[11px] text-[#8a8985]">
        <strong>Disclaimer:</strong> Legal Analyzer is an automated system. Always verify outputs with legal counsel before executing.
      </footer>
    </div>
  );
}


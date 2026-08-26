"use client";

import React, { useState, useEffect } from "react";
import { apiClient, DeepExtractionResponse } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";

interface RedlineWorkbenchProps {
  documentId: string;
}

export function RedlineWorkbench({ documentId }: RedlineWorkbenchProps) {
  const [data, setData] = useState<DeepExtractionResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const extraction = await apiClient.getDeepExtraction(documentId);
        setData(extraction);
      } catch (err: any) {
        setError(err.message || "Failed to load redlines");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [documentId]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).catch(err => {
      console.error("Failed to copy text: ", err);
    });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full rounded-sm" />
        <Skeleton className="h-64 w-full rounded-sm" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
        <CardContent className="p-6 text-center text-[#8a8985]">
          {error || "Failed to load redlines."}
        </CardContent>
      </Card>
    );
  }

  const { redline_suggestions } = data;

  if (!redline_suggestions || redline_suggestions.length === 0) {
    return (
      <EmptyState 
        title="No Redlines Found" 
        description="No redline suggestions. All clauses appear to use standard language." 
      />
    );
  }

  return (
    <div className="space-y-6">
      {redline_suggestions.map((redline, index) => (
        <Card key={index} className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
          <CardHeader className="border-b border-[#e0dfdb] pb-4 flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <CardTitle className="text-lg text-[#0d1b2a]">{redline.clause_type}</CardTitle>
              {redline.severity ? (
                <Badge variant={redline.severity.toLowerCase() === "high" ? "high" : redline.severity.toLowerCase() === "medium" ? "medium" : "low"}>
                  {redline.severity} Risk
                </Badge>
              ) : (
                <Badge variant="neutral">Suggested Redline</Badge>
              )}
            </div>
            <Button 
              variant="outline" 
              onClick={() => handleCopy(redline.suggested_replacement)}
              className="border-[#0d1b2a] text-[#0d1b2a] hover:bg-[#0d1b2a] hover:text-[#faf9f6]"
            >
              Copy Suggestion
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="grid grid-cols-1 md:grid-cols-2">
              <div className="p-6 border-b md:border-b-0 md:border-r border-[#e0dfdb] bg-[#fdf2f2]">
                <h4 className="text-xs font-semibold text-[#8a8985] uppercase tracking-wider mb-3">Original Text</h4>
                <p className="text-sm text-[#0d1b2a] whitespace-pre-wrap font-mono">
                  {redline.original_text}
                </p>
              </div>
              <div className="p-6 bg-[#f0fdf4]">
                <h4 className="text-xs font-semibold text-[#8a8985] uppercase tracking-wider mb-3">Suggested Replacement</h4>
                <p className="text-sm text-[#0d1b2a] whitespace-pre-wrap font-mono">
                  {redline.suggested_replacement}
                </p>
              </div>
            </div>
            <div className="p-4 border-t border-[#e0dfdb] bg-[#faf9f6]">
              <p className="text-sm text-[#0d1b2a] italic">
                <span className="font-semibold not-italic mr-2">Rationale:</span>
                {redline.rationale}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

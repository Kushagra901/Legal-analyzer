"use client";

import React, { useState, useEffect } from "react";
import { apiClient, DeepExtractionResponse } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface DealTermsMatrixProps {
  documentId: string;
}

export function DealTermsMatrix({ documentId }: DealTermsMatrixProps) {
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
        setError(err.message || "Failed to load deal terms");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [documentId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full rounded-sm" />
        <Skeleton className="h-48 w-full rounded-sm" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
        <CardContent className="p-6 text-center text-[#8a8985]">
          {error || "No deal terms available."}
        </CardContent>
      </Card>
    );
  }

  const { deal_terms, missing_protections, executive_summary } = data;

  return (
    <div className="space-y-6">
      <Card className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
        <CardHeader className="border-b border-[#e0dfdb] pb-4">
          <CardTitle className="text-lg text-[#0d1b2a]">Executive Summary</CardTitle>
        </CardHeader>
        <CardContent className="pt-4 text-sm text-[#0d1b2a]">
          {executive_summary}
        </CardContent>
      </Card>

      <Card className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
        <CardHeader className="border-b border-[#e0dfdb] pb-4">
          <CardTitle className="text-lg text-[#0d1b2a]">Key Deal Terms</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableBody>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985] w-1/3">Document Type</TableCell>
                <TableCell className="text-[#0d1b2a]">{deal_terms.document_type || "N/A"}</TableCell>
              </TableRow>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985]">Parties</TableCell>
                <TableCell className="text-[#0d1b2a]">
                  {deal_terms.parties && deal_terms.parties.length > 0 ? (
                    <ul className="list-disc list-inside">
                      {deal_terms.parties.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  ) : "N/A"}
                </TableCell>
              </TableRow>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985]">Effective Date</TableCell>
                <TableCell className="text-[#0d1b2a]">{deal_terms.effective_date || "N/A"}</TableCell>
              </TableRow>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985]">Expiration Date</TableCell>
                <TableCell className="text-[#0d1b2a]">{deal_terms.expiration_date || "N/A"}</TableCell>
              </TableRow>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985]">Auto-Renewal</TableCell>
                <TableCell className="text-[#0d1b2a]">
                  <div className="flex items-center gap-2">
                    {deal_terms.auto_renewal ? "Yes" : "No"}
                    {deal_terms.auto_renewal && deal_terms.renewal_notice_days && (
                      <Badge variant="neutral" className="rounded-none border-[#e0dfdb] text-xs text-[#0d1b2a]">
                        {deal_terms.renewal_notice_days} Days Notice
                      </Badge>
                    )}
                  </div>
                </TableCell>
              </TableRow>
              <TableRow className="border-b border-[#e0dfdb]">
                <TableCell className="font-medium text-[#8a8985]">Governing Law & Jurisdiction</TableCell>
                <TableCell className="text-[#0d1b2a]">
                  {deal_terms.governing_law || "N/A"} / {deal_terms.jurisdiction || "N/A"}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {missing_protections && missing_protections.length > 0 && (
        <Card className="rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
          <CardHeader className="border-b border-[#e0dfdb] pb-4">
            <CardTitle className="text-lg text-[#0d1b2a]">Missing Protections</CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-3">
            {missing_protections.map((protection, i) => (
              <div 
                key={i} 
                className="p-3 bg-white border border-[#e0dfdb] rounded-sm text-sm text-[#0d1b2a]"
                style={{ borderLeft: "4px solid rgba(192, 57, 43, 0.2)" }}
              >
                {protection}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

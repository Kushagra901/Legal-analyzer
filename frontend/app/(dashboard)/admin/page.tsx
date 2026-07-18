"use client";

/**
 * @file page.tsx
 * @description Admin page for system audits, logging, and pipeline monitor dashboard.
 */

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { apiClient } from "@/lib/api";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";

interface AuditLogItem {
  id: string;
  action: string;
  document_id: string;
  user: string;
  timestamp: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkSessionAndFetch = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        router.push("/login");
        return;
      }
      try {
        setIsLoading(true);
        const dataLogs = await apiClient.fetchAuditLogs();
        setLogs(dataLogs);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load audit logs.");
      } finally {
        setIsLoading(false);
      }
    };
    checkSessionAndFetch();
  }, [router]);

  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] font-sans">
      <header className="border-b border-[#e0dfdb] bg-white px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Link href="/dashboard" className="text-xs text-[#5c5b57] hover:underline uppercase tracking-wider font-semibold">
            &larr; Dashboard
          </Link>
          <h1 className="font-serif text-xl font-normal text-[#0d1b2a]">System Administration</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-8 space-y-8">
        <section className="border border-[#e0dfdb] bg-white p-6 rounded-none">
          <h2 className="font-serif text-lg text-[#0d1b2a] mb-2">Audit Logs</h2>
          <p className="text-xs text-[#5c5b57] mb-6">
            Review history logs, uploads, and critical administrative activities on documents.
          </p>

          {error && (
            <div className="mb-4 p-3 bg-[#faf9f6] border border-[#ff4d4d] text-[#ff4d4d] text-xs flex items-center justify-between">
              <span>{error}</span>
              <button 
                onClick={() => setError(null)} 
                className="text-xs font-bold hover:underline cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="space-y-4">
              <div className="border-b border-[#e0dfdb] pb-4 flex justify-between items-center animate-pulse">
                <div className="h-4 bg-[#e0dfdb] w-1/4"></div>
                <div className="h-4 bg-[#e0dfdb] w-1/3"></div>
                <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
              </div>
              <div className="border-b border-[#e0dfdb] pb-4 flex justify-between items-center animate-pulse">
                <div className="h-4 bg-[#e0dfdb] w-1/4"></div>
                <div className="h-4 bg-[#e0dfdb] w-1/3"></div>
                <div className="h-4 bg-[#e0dfdb] w-1/6"></div>
              </div>
            </div>
          ) : logs.length === 0 ? (
            <EmptyState 
              title="No logs recorded" 
              description="Upload a document or trigger an action to populate the system audit trail."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="py-2">Log ID</TableHead>
                  <TableHead className="py-2">Action</TableHead>
                  <TableHead className="py-2">Document ID</TableHead>
                  <TableHead className="py-2">User</TableHead>
                  <TableHead className="py-2 text-right">Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="py-3 font-mono">{log.id}</TableCell>
                    <TableCell className="py-3 font-semibold text-[#0d1b2a]">
                      {log.action}
                    </TableCell>
                    <TableCell className="py-3 font-mono">
                      {log.document_id}
                    </TableCell>
                    <TableCell className="py-3">{log.user}</TableCell>
                    <TableCell className="py-3 text-right text-[#5c5b57] font-mono">
                      {log.timestamp}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </main>
    </div>
  );
}

"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ErrorBoundary } from "@/components/ui/error-boundary";


export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const navLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/documents/upload", label: "Upload Document" },
    { href: "/review", label: "Clause Review Queue" },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-page)] text-[var(--text-main)]">
      {/* Top Header Navigation - Hidden when printing */}
      <header className="no-print border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link href="/dashboard" className="font-serif text-xl font-bold tracking-tight text-[var(--accent-primary)]">
            LEGAL ANALYZER
          </Link>
          <nav className="flex items-center space-x-6 text-xs font-semibold uppercase tracking-wider">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`transition-colors duration-150 py-1 border-b-2 ${
                    isActive
                      ? "border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold"
                      : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-4 text-xs">
          <span className="text-[var(--text-muted)] border-r border-[var(--border-subtle)] pr-4">
            Licensed User Mode
          </span>
          <button
            onClick={handleSignOut}
            className="text-[var(--text-muted)] hover:text-[var(--text-main)] font-semibold uppercase tracking-wider cursor-pointer"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>


      {/* Mandatory Legal Disclaimer Footer */}
      <footer className="no-print border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] py-4 px-6 text-center text-[11px] text-[var(--text-muted)]">
        <p className="max-w-4xl mx-auto">
          <strong>LEGAL DISCLAIMER:</strong> This AI tool provides first-pass document extraction, risk flagging, and automated summarization to assist legal workflow. 
          It does not provide licensed legal advice and does not substitute for review by a qualified legal professional.
        </p>
      </footer>
    </div>
  );
}

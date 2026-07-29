"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        setError(authError.message);
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center p-6 bg-[var(--bg-page)] text-[var(--text-main)]">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="font-serif text-3xl font-bold text-[var(--accent-primary)]">
            LEGAL ANALYZER
          </h1>
          <p className="text-xs uppercase tracking-wider text-[var(--text-muted)] font-semibold">
            AI-Assisted Contract & Document Intelligence
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign In to Workspace</CardTitle>
            <CardDescription>
              Enter your credentials to access contract analysis and audit logs.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              {error && (
                <div className="p-3 bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)] text-xs">
                  {error}
                </div>
              )}
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Email Address
                </label>
                <Input
                  type="email"
                  required
                  placeholder="lawyer@firm.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Password
                </label>
                <Input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Authenticating..." : "Sign In"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs">
            <span className="text-[var(--text-muted)]">Don't have an account?</span>
            <Link href="/signup" className="font-semibold text-[var(--accent-primary)] hover:underline">
              Create Account
            </Link>
          </CardFooter>
        </Card>

        <p className="text-[11px] text-center text-[var(--text-muted)] leading-relaxed">
          Assists legal review — does not replace a licensed attorney.
        </p>
      </div>
    </div>
  );
}

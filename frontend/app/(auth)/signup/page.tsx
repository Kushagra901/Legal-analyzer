"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { error: authError } = await supabase.auth.signUp({
        email,
        password,
      });

      if (authError) {
        setError(authError.message);
      } else {
        setSuccess(true);
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
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
            Registration & Workspace Setup
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Create Attorney Account</CardTitle>
            <CardDescription>
              Register your email to manage contracts and access compliance audit tools.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSignup} className="space-y-4">
              {error && (
                <div className="p-3 bg-[var(--risk-high-bg)] border border-[var(--risk-high)] text-[var(--risk-high)] text-xs">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 bg-[var(--risk-low-bg)] border border-[var(--risk-low)] text-[var(--risk-low)] text-xs font-semibold">
                  Account successfully created. Redirecting to workspace...
                </div>
              )}
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Work Email Address
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
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Confirm Password
                </label>
                <Input
                  type="password"
                  required
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Registering..." : "Create Account"}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs">
            <span className="text-[var(--text-muted)]">Already have an account?</span>
            <Link href="/login" className="font-semibold text-[var(--accent-primary)] hover:underline">
              Sign In
            </Link>
          </CardFooter>
        </Card>

        <p className="text-[11px] text-center text-[var(--text-muted)] leading-relaxed">
          Legal Analyzer assists first-pass contract extraction — does not constitute formal legal counsel.
        </p>
      </div>
    </div>
  );
}

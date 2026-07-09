"use client";

/**
 * @file page.tsx
 * @description Login page component for user authentication using Supabase.
 */

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!email || !password) {
      setErrorMessage("Please enter both email and password.");
      setIsSubmitting(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw new Error(error.message);
      }

      if (data?.session) {
        setSuccessMessage("Sign in successful! Redirecting...");
        setTimeout(() => {
          router.push("/dashboard");
        }, 1200);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid login credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] flex flex-col justify-center items-center p-6 font-sans">
      <div className="w-full max-w-md bg-white border border-[#e0dfdb] p-8 rounded-none">
        <h1 className="font-serif text-3xl font-normal mb-6 text-[#0d1b2a]">
          Legal Analyzer
        </h1>
        <p className="text-sm text-[#5c5b57] mb-6">
          Please sign in to access your dashboard.
        </p>

        {errorMessage && (
          <div className="mb-4 p-3 bg-[#faf9f6] border border-[#ff4d4d] text-[#ff4d4d] text-xs">
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div className="mb-4 p-3 bg-[#faf9f6] border border-[#2b9348] text-[#2b9348] text-xs">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-[#e0dfdb] px-3 py-2 text-sm bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none"
              placeholder="name@company.com"
              disabled={isSubmitting}
              required
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-[#e0dfdb] px-3 py-2 text-sm bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none"
              placeholder="••••••••"
              disabled={isSubmitting}
              required
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] text-sm py-2.5 font-semibold transition-colors duration-200 rounded-none uppercase tracking-wider disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-[#e0dfdb] text-center text-xs text-[#5c5b57]">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-[#0d1b2a] underline font-semibold">
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}

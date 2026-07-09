"use client";

/**
 * @file page.tsx
 * @description Signup page component for user registration using Supabase Auth.
 */

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    // 1. Validation
    if (!email || !password || !confirmPassword) {
      setErrorMessage("All fields are required.");
      setIsSubmitting(false);
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match.");
      setIsSubmitting(false);
      return;
    }

    if (password.length < 6) {
      setErrorMessage("Password must be at least 6 characters.");
      setIsSubmitting(false);
      return;
    }

    try {
      // 2. Supabase SignUp
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      });

      if (error) {
        throw new Error(error.message);
      }

      // If signUp succeeded, check if the session is available
      if (data?.session) {
        setSuccessMessage("Account created successfully! Redirecting...");
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
      } else {
        setSuccessMessage("Account created successfully! Please check your email to verify your address.");
        setEmail("");
        setPassword("");
        setConfirmPassword("");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred during signup.");
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
          Create an account to start reviewing your legal documents.
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

        <form onSubmit={handleSignup} className="space-y-4">
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

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {isSubmitting ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-[#e0dfdb] text-center text-xs text-[#5c5b57]">
          Already have an account?{" "}
          <Link href="/login" className="text-[#0d1b2a] underline font-semibold">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

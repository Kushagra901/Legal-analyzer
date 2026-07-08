/**
 * @file page.tsx
 * @description Signup page component for user registration.
 */

import React from "react";
import Link from "next/link";

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-[#faf9f6] text-[#1c1c1c] flex flex-col justify-center items-center p-6 font-sans">
      <div className="w-full max-w-md bg-white border border-[#e0dfdb] p-8 rounded-none">
        <h1 className="font-serif text-3xl font-normal mb-6 text-[#0d1b2a]">
          Legal Analyzer
        </h1>
        <p className="text-sm text-[#5c5b57] mb-6">
          Create an account to start reviewing your legal documents.
        </p>

        <form className="space-y-4">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Email Address
            </label>
            <input
              type="email"
              className="w-full border border-[#e0dfdb] px-3 py-2 text-sm bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none"
              placeholder="name@company.com"
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Password
            </label>
            <input
              type="password"
              className="w-full border border-[#e0dfdb] px-3 py-2 text-sm bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#5c5b57] mb-1 font-semibold">
              Confirm Password
            </label>
            <input
              type="password"
              className="w-full border border-[#e0dfdb] px-3 py-2 text-sm bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] text-sm py-2.5 font-semibold transition-colors duration-200 rounded-none uppercase tracking-wider"
          >
            Create Account
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


/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Shield, ArrowRight } from 'lucide-react';
import { UserSession } from '../types';

interface LoginViewProps {
  onLogin: (session: UserSession) => void;
}

export default function LoginView({ onLogin }: LoginViewProps) {
  const [email, setEmail] = useState('counsel@enterprise.legal');
  const [name, setName] = useState('Margaret Vance');
  const [role, setRole] = useState('Senior Legal Counsel');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      onLogin({
        name,
        role,
        email,
        isLoggedIn: true,
      });
      setIsSubmitting(false);
    }, 800);
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-8 bg-bg-warm" id="login-container">
      {/* Upper header block */}
      <div className="flex items-center space-x-2 text-ink-dark/80" id="login-header-logo">
        <Shield className="w-5 h-5 text-accent-forest" />
        <span className="font-mono text-xs tracking-wider uppercase font-semibold">Legal Analyzer Workspace</span>
      </div>

      {/* Centered Sign-in card */}
      <div className="max-w-md w-full mx-auto my-auto py-12" id="login-card">
        <div className="text-left mb-8" id="login-intro">
          <h1 className="font-serif text-3xl font-medium tracking-tight text-ink-dark mb-3">
            Sign In to Legal Analyzer
          </h1>
          <p className="text-ink-muted text-sm leading-relaxed">
            Access secure document analysis workspace. All files are parsed using sovereign client parameters and certified machine learning models.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" id="login-form">
          <div className="space-y-1.5" id="form-group-email">
            <label className="block text-xs font-mono uppercase tracking-wider text-ink-dark/80" htmlFor="email-input">
              Corporate Email Address
            </label>
            <input
              id="email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-transparent border border-border-subtle px-3 py-2.5 text-sm rounded-none focus:outline-none focus:border-accent-forest font-sans transition-colors"
              placeholder="name@company.com"
            />
          </div>

          <div className="space-y-1.5" id="form-group-name">
            <label className="block text-xs font-mono uppercase tracking-wider text-ink-dark/80" htmlFor="name-input">
              Full Legal Name
            </label>
            <input
              id="name-input"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-transparent border border-border-subtle px-3 py-2.5 text-sm rounded-none focus:outline-none focus:border-accent-forest font-sans transition-colors"
              placeholder="e.g. Margaret Vance"
            />
          </div>

          <div className="space-y-1.5" id="form-group-role">
            <label className="block text-xs font-mono uppercase tracking-wider text-ink-dark/80" htmlFor="role-select">
              Professional Role
            </label>
            <select
              id="role-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-transparent border border-border-subtle px-3 py-2.5 text-sm rounded-none focus:outline-none focus:border-accent-forest font-sans transition-colors"
            >
              <option value="Senior Legal Counsel">Senior Legal Counsel</option>
              <option value="Contract Specialist">Contract Specialist</option>
              <option value="Compliance Director">Compliance Director</option>
              <option value="External Legal Auditor">External Legal Auditor</option>
            </select>
          </div>

          <button
            id="login-submit-button"
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-accent-forest hover:bg-opacity-90 text-white font-sans text-sm tracking-wide py-3 px-4 flex items-center justify-center space-x-2 transition-all disabled:opacity-50 cursor-pointer"
          >
            <span>{isSubmitting ? 'Authenticating Credentials...' : 'Access Document Workspace'}</span>
            {!isSubmitting && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-border-subtle flex items-center justify-between text-xs text-ink-muted font-mono" id="login-footer-info">
          <span>Encryption: AES-256</span>
          <span>Workspace Session: Secure Tokenized</span>
        </div>
      </div>

      {/* Footer Block */}
      <div className="text-center text-xs text-ink-muted font-mono mt-8" id="login-disclaimer">
        © 2026 Legal Analyzer Corporation. Classified for Professional Advisory Purposes.
      </div>
    </div>
  );
}

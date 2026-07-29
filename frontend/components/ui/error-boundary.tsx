"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error caught by ErrorBoundary:", error, errorInfo);
    Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="my-8 max-w-2xl mx-auto border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-main)] p-8 rounded-none">
          <h2 className="font-serif text-2xl font-bold tracking-tight text-[var(--accent-primary)] mb-3">
            An Application Error Occurred
          </h2>
          <p className="text-xs text-[var(--text-muted)] mb-6">
            The application encountered an unexpected runtime exception during rendering.
          </p>

          {this.state.error && (
            <div className="p-4 mb-6 border border-[var(--border-subtle)] bg-[var(--bg-page)] text-xs font-mono break-words text-[var(--text-main)]">
              {this.state.error.message || String(this.state.error)}
            </div>
          )}

          <div className="flex items-center space-x-4">
            <Link
              href="/dashboard"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-4 py-2 text-xs font-semibold uppercase tracking-wider bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-hover)] transition-colors duration-150 rounded-none inline-flex items-center justify-center cursor-pointer"
            >
              Return to Dashboard
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

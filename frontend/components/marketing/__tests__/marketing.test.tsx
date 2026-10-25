/**
 * @file marketing.test.tsx
 * @description Unit tests for marketing landing page components with jsdom IntersectionObserver mock.
 */

import React from "react";
import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { HeroMockup } from "../hero-mockup";
import { HowItWorksSection } from "../how-it-works-section";
import { ResultsSection } from "../results-section";
import { SampleMemoSection } from "../sample-memo-section";
import { TrustAndFaqSection } from "../trust-and-faq-section";
import { FooterCtaSection } from "../footer-cta-section";

beforeAll(() => {
  class MockIntersectionObserver {
    observe = () => null;
    unobserve = () => null;
    disconnect = () => null;
  }
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    configurable: true,
    value: MockIntersectionObserver,
  });
});

describe("Marketing Landing Page Components", () => {
  it("renders HeroMockup with MSA title and overall score", () => {
    render(<HeroMockup />);
    expect(screen.getByText(/SAMPLE CONTRACT — MASTER SERVICES AGREEMENT/i)).toBeDefined();
    expect(screen.getByText(/Overall Document Score:/i)).toBeDefined();
    expect(screen.getByText(/60 \/ 100/i)).toBeDefined();
  });

  it("renders HowItWorksSection with 4 steps and scoring table", () => {
    render(<HowItWorksSection />);
    expect(screen.getByText("How it works")).toBeDefined();
    expect(screen.getByText("Upload a contract")).toBeDefined();
    expect(screen.getByText("Clause audit & risk scoring")).toBeDefined();
    expect(screen.getByText("11.2 Indemnification and third-party claims")).toBeDefined();
  });

  it("renders ResultsSection with dual-pane analysis and redline suggestions", () => {
    render(<ResultsSection />);
    expect(screen.getByText("Interactive split-pane results")).toBeDefined();
    expect(screen.getByText(/Suggested replacement text, with the reasoning/i)).toBeDefined();
    expect(screen.getByText(/Makes the termination right mutual/i)).toBeDefined();
  });

  it("renders SampleMemoSection with memorandum headers and ratings", () => {
    render(<SampleMemoSection />);
    expect(screen.getByText("Sample memo")).toBeDefined();
    expect(screen.getByText("MEMORANDUM OF COUNSEL")).toBeDefined();
    expect(screen.getByText("Download sample memo →")).toBeDefined();
  });

  it("renders TrustAndFaqSection with review queue message and FAQ questions", () => {
    render(<TrustAndFaqSection />);
    expect(screen.getByText(/Flagged clauses wait in a review queue/i)).toBeDefined();
    expect(screen.getByText("Frequently asked questions")).toBeDefined();
    expect(screen.getByText("Does it replace a lawyer?")).toBeDefined();
  });

  it("renders FooterCtaSection with start CTA and disclaimer", () => {
    render(<FooterCtaSection />);
    expect(screen.getByText("Start with one contract.")).toBeDefined();
    expect(screen.getByText(/Legal Analyzer provides automated analysis to assist in contract triage/i)).toBeDefined();
  });
});

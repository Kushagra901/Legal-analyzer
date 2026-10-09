import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { Badge } from "../badge";

describe("Badge Component", () => {
  it("renders with children and default neutral variant", () => {
    render(<Badge>Default Badge</Badge>);
    const badge = screen.getByText("Default Badge");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("text-[var(--text-muted)]");
  });

  it("applies low risk variant styles", () => {
    render(<Badge variant="low">Low Risk</Badge>);
    const badge = screen.getByText("Low Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("text-[var(--risk-low)]");
    expect(badge.className).toContain("border-[var(--risk-low)]");
  });

  it("applies medium risk variant styles", () => {
    render(<Badge variant="medium">Medium Risk</Badge>);
    const badge = screen.getByText("Medium Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("text-[var(--risk-medium)]");
    expect(badge.className).toContain("border-[var(--risk-medium)]");
  });

  it("applies high risk variant styles", () => {
    render(<Badge variant="high">High Risk</Badge>);
    const badge = screen.getByText("High Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("text-[var(--risk-high)]");
    expect(badge.className).toContain("border-[var(--risk-high)]");
  });

  it("appends custom className and passes through HTML attributes", () => {
    render(
      <Badge variant="neutral" className="custom-test-class" data-testid="custom-badge">
        Custom Badge
      </Badge>
    );
    const badge = screen.getByTestId("custom-badge");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("custom-test-class");
  });
});

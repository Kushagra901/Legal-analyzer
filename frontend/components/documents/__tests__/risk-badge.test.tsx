import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { RiskBadge } from "../risk-badge";

describe("RiskBadge Component", () => {
  it("renders low risk level with green style classes", () => {
    render(<RiskBadge level="low" />);
    const badge = screen.getByText("low Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-green-100");
    expect(badge.className).toContain("text-green-800");
    expect(badge.className).toContain("border-green-200");
  });

  it("renders medium risk level with yellow style classes", () => {
    render(<RiskBadge level="medium" />);
    const badge = screen.getByText("medium Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-yellow-100");
    expect(badge.className).toContain("text-yellow-800");
    expect(badge.className).toContain("border-yellow-200");
  });

  it("renders high risk level with red style classes", () => {
    render(<RiskBadge level="high" />);
    const badge = screen.getByText("high Risk");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-red-100");
    expect(badge.className).toContain("text-red-800");
    expect(badge.className).toContain("border-red-200");
  });
});

import React from "react";

export const ReportView = () => {
  return (
    <div className="border border-[#e0dfdb] bg-white p-8 rounded-none space-y-6">
      <h2 className="font-serif text-xl border-b border-[#e0dfdb] pb-2 text-[#0d1b2a]">Legal Assessment Report</h2>
      <div className="space-y-4">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#5c5b57]">Executive Summary</h3>
          <p className="text-xs text-[#1c1c1c] leading-relaxed mt-1">
            This document outlines risk metrics and summary analyses for the reviewed contract.
          </p>
        </div>
      </div>
    </div>
  );
};

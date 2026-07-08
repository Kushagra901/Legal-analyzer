/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Loader2, ShieldCheck, Check, AlertCircle } from 'lucide-react';

interface ProcessingViewProps {
  documentName: string;
}

export default function ProcessingView({ documentName }: ProcessingViewProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    { label: "Extracting contract segments & structural text", duration: 1500 },
    { label: "Identifying legal definitions & unilateral triggers", duration: 2000 },
    { label: "Scoring contract risk & compliance index weights", duration: 1500 },
    { label: "Compiling executive memorandum & rev drafting suggestions", duration: 1200 }
  ];

  useEffect(() => {
    let timer: NodeJS.Timeout;
    const runSteps = (index: number) => {
      if (index < steps.length) {
        timer = setTimeout(() => {
          setCurrentStep(index + 1);
          runSteps(index + 1);
        }, steps[index].duration);
      }
    };
    runSteps(0);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="max-w-md w-full mx-auto py-24 px-6 text-center" id="processing-view-container">
      <div className="mb-8" id="processing-icon-block">
        <Loader2 className="w-10 h-10 text-accent-forest animate-spin mx-auto stroke-1" />
      </div>

      <div className="mb-8" id="processing-text-block">
        <h3 className="font-serif text-2xl font-medium text-ink-dark mb-2">
          Performing Audit Analysis
        </h3>
        <p className="text-xs font-mono text-ink-muted uppercase tracking-wider">
          Document: {documentName}
        </p>
      </div>

      {/* Structured Step Progress Checklist */}
      <div className="border border-border-subtle bg-bg-card p-6 text-left space-y-4" id="processing-steps-list">
        {steps.map((step, idx) => {
          const isDone = currentStep > idx;
          const isActive = currentStep === idx;

          return (
            <div
              key={idx}
              id={`processing-step-${idx}`}
              className={`flex items-start space-x-3 transition-opacity duration-300 ${
                isDone || isActive ? 'opacity-100' : 'opacity-40'
              }`}
            >
              <div className="mt-0.5" id={`step-indicator-${idx}`}>
                {isDone ? (
                  <Check className="w-4 h-4 text-risk-low stroke-[2.5px]" />
                ) : isActive ? (
                  <span className="w-4 h-4 border-2 border-accent-forest border-t-transparent rounded-full animate-spin inline-block"></span>
                ) : (
                  <span className="w-4 h-4 border border-border-subtle rounded-full inline-block bg-transparent"></span>
                )}
              </div>
              <div>
                <span className={`text-sm font-sans ${isActive ? 'text-ink-dark font-medium' : 'text-ink-dark/80'}`}>
                  {step.label}
                </span>
                {isActive && (
                  <span className="block text-xs text-accent-forest font-mono uppercase tracking-wider animate-pulse mt-0.5">
                    Analyzing segment data...
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 text-xs text-ink-muted font-mono" id="processing-disclaimer">
        <span>Processing via sovereign AI engine • Secure isolated sandbox</span>
      </div>
    </div>
  );
}

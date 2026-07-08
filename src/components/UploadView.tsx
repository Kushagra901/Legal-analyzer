/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef } from 'react';
import { Upload, FileText, ArrowLeft, AlertCircle, Sparkles, Check } from 'lucide-react';

interface UploadViewProps {
  onBackToDashboard: () => void;
  onStartAnalysis: (text: string, name: string) => void;
}

// Full legal template bodies matching our preloads for seamless user interaction
const TEMPLATES = [
  {
    name: "Corporate NDA (Bilateral / Balanced)",
    filename: "Mutual NDA - apex_horizon.txt",
    description: "Standard mutual non-disclosure contract with bilateral exclusions and survival caps.",
    text: `MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement (the "Agreement") is entered into as of October 12, 2025 (the "Effective Date") by and between Apex Tech Solutions, LLC ("Apex"), and Horizon Ventures, LP ("Horizon").

1. Purpose. The parties wish to explore a potential business relationship of mutual interest (the "Transaction"). In connection with the Transaction, either party (as the "Disclosing Party") may disclose to the other party (as the "Receiving Party") certain proprietary or confidential information.

2. Confidential Information. "Confidential Information" means any information or materials disclosed by the Disclosing Party to the Receiving Party that is either designated as confidential in writing or should reasonably be understood to be confidential given the nature of the information. Confidential Information does not include information that: (a) is or becomes publicly known through no breach of this Agreement; (b) was already in the Receiving Party's lawful possession; or (c) is independently developed by the Receiving Party without reference to or reliance upon the Disclosing Party's Confidential Information.

3. Obligations of Confidentiality. The Receiving Party agrees: (a) to hold the Disclosing Party's Confidential Information in strict confidence and use at least a reasonable degree of care to prevent unauthorized disclosure; (b) to use such Confidential Information solely for the Purpose; and (c) to restrict access to such Confidential Information to its employees, affiliates, or advisors who need to know and are bound by confidentiality obligations at least as protective as those herein.

4. Term and Termination. This Agreement shall govern all disclosures made during a period of one (1) year from the Effective Date. The Receiving Party's obligations under this Agreement with respect to Confidential Information disclosed hereunder shall survive for a period of three (3) years from the date of disclosure.

5. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

6. Governing Law and Jurisdiction. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles. Any legal action arising hereunder shall be brought exclusively in the state or federal courts located in Wilmington, Delaware.

IN WITNESS WHEREOF, the parties have executed this Mutual Non-Disclosure Agreement as of the Effective Date.`
  },
  {
    name: "Enterprise SaaS Terms (Vendor-biased / Highly Unbalanced)",
    filename: "CloudScale SaaS Agreement.txt",
    description: "Highly aggressive SaaS terms including customer-only indemnification and microscopic liability caps.",
    text: `SOFTWARE-AS-A-SERVICE (SaaS) AGREEMENT

This SaaS Agreement (the "Agreement") is made and entered into by and between CloudScale Enterprise Inc. ("Provider") and Global Retail Corp. ("Customer") as of August 24, 2025.

1. Services and License. Provider grants Customer a non-transferable, non-exclusive, revocable license to access the CloudScale Analytics Suite (the "Service") during the applicable Subscription Term.

2. Service Level Agreement & Support. Provider will use commercially reasonable efforts to make the Service available 99.0% of the time, measured monthly, excluding scheduled maintenance. Support is provided during standard business hours only (9 AM - 5 PM EST, Monday through Friday, excluding holidays).

3. Unilateral Indemnification. Customer shall defend, indemnify, and hold harmless Provider and its officers, directors, and employees from and against any and all claims, losses, damages, liabilities, and expenses (including reasonable attorneys' fees) arising out of or relating to Customer's use of the Service, breach of this Agreement, or violation of third-party intellectual property rights. PROVIDER HAS NO INDEMNIFICATION OBLIGATION TO CUSTOMER UNDER ANY CIRCUMSTANCE.

4. Unbalanced Limitation of Liability. IN NO EVENT SHALL PROVIDER'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT, OR OTHERWISE, EXCEED THE TOTAL AMOUNT ACTUALLY PAID BY CUSTOMER TO PROVIDER IN THE ONE (1) MONTH IMMEDIATELY PRECEDING THE EVENT GIVING RISE TO LIABILITY. CUSTOMER ACKNOWLEDGES THAT THIS LIMITATION IS A CRITICAL BASIS OF THE BARGAIN.

5. IP Ownership. All right, title, and interest in and to the Service, including all software, source code, documentation, modifications, and any user feedback or suggestions, shall remain exclusively with Provider. Customer grants Provider an unrestricted, royalty-free, perpetual, irrevocable license to use, reproduce, modify, and exploit any feedback provided by Customer for any purpose whatsoever.

6. Governing Law and Severability. This Agreement is governed by the laws of the State of New York. If any court of competent jurisdiction finds any provision of this Agreement invalid, such provision shall be modified to reflect the parties' intent, and the remainder of the Agreement shall continue in full force.`
  },
  {
    name: "Independent Contractor Consulting Contract",
    filename: "Jenkins Advisory Agreement.txt",
    description: "Contains an overly long 18-month North American non-compete and Net-90 slow payout terms.",
    text: `INDEPENDENT CONTRACTOR CONSULTING AGREEMENT

This Consulting Agreement (the "Agreement") is dated June 1, 2025, between Alpha Business Advisory ("Client") and Sarah Jenkins ("Consultant").

1. Services. Consultant agrees to perform the digital strategy consulting services described in Exhibit A (the "Services") in a professional, timely manner.

2. Compensation and Payment. Client shall pay Consultant $150 per hour for Services rendered. Consultant shall submit monthly invoices. Client shall pay all approved invoices within ninety (90) days of receipt. Consultant shall bear all expenses unless pre-approved in writing.

3. Complete Intellectual Property Assignment. Consultant agrees that all deliverables, designs, reports, software code, written materials, ideas, and inventions created, conceived, or developed by Consultant under this Agreement (the "Work Product") shall belong exclusively to Client. Consultant hereby unconditionally and irrevocably assigns, transfers, and conveys to Client all right, title, and interest worldwide in and to the Work Product. Consultant agrees to sign any documents necessary to assist Client in registering and protecting these rights. Consultant waives all moral rights in the Work Product.

4. Non-Competition. During the term of this Agreement and for a period of eighteen (18) months thereafter, Consultant shall not, directly or indirectly, perform consulting services, work for, or engage in any business activity that competes directly with Client's business within North America.

5. Term and Termination. This Agreement commences on the date hereof and continues until terminated. Either party may terminate this Agreement for convenience upon sixty (60) days prior written notice. Client may terminate immediately for cause if Consultant breaches any confidentiality or IP provision.`
  }
];

export default function UploadView({ onBackToDashboard, onStartAnalysis }: UploadViewProps) {
  const [inputText, setInputText] = useState('');
  const [docName, setDocName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle Drag events
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);

    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  const processFile = (file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      setError("File exceeds maximum allowance of 5.0 MB. Please upload a smaller legal draft.");
      return;
    }

    if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
      setError("Unreadable scan format. System currently accepts plain text (.txt) or markdown (.md) documents to ensure accurate compliance auditing.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (text && text.trim()) {
        setInputText(text);
        setDocName(file.name);
        setSelectedTemplateIndex(null);
      } else {
        setError("File appears empty. Please upload a valid text document containing contract clauses.");
      }
    };
    reader.onerror = () => {
      setError("An error occurred while loading this document. Please verify file state and retry.");
    };
    reader.readAsText(file);
  };

  const handleSelectTemplate = (index: number) => {
    setError(null);
    const template = TEMPLATES[index];
    setInputText(template.text);
    setDocName(template.filename);
    setSelectedTemplateIndex(index);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) {
      setError("Please paste contract clauses, upload a file, or select a preloaded legal template to begin analysis.");
      return;
    }
    const finalName = docName.trim() || "Un-named Contract.txt";
    onStartAnalysis(inputText, finalName);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 text-left" id="upload-container">
      {/* Upper Navigation link */}
      <button
        id="upload-back-btn"
        onClick={onBackToDashboard}
        className="flex items-center space-x-1.5 text-xs text-ink-muted font-mono uppercase tracking-wider hover:text-ink-dark transition-colors mb-6 cursor-pointer"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Return to Dashboard</span>
      </button>

      <div className="mb-8" id="upload-intro-text">
        <h1 className="font-serif text-3xl font-medium tracking-tight text-ink-dark mb-2">
          New Document Compliance Audit
        </h1>
        <p className="text-ink-muted text-sm leading-relaxed max-w-2xl">
          Upload or paste any agreement. The analyzer parses text structures in real-time, extracts core clauses, cross-references standard baseline definitions, and flags aggressive terms.
        </p>
      </div>

      {error && (
        <div className="bg-risk-high-bg border border-risk-high/30 p-4 mb-6 flex items-start space-x-3 text-sm text-risk-high" id="upload-error-banner">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <div>
            <span className="font-semibold block">Auditing Restriction Identified</span>
            <span className="text-xs leading-relaxed">{error}</span>
          </div>
        </div>
      )}

      {/* Grid: Templates (Left) and Upload/Paste (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8" id="upload-workspace">
        
        {/* Left Side: Preloaded Templates - Invaluable for testing */}
        <div className="lg:col-span-4 space-y-4" id="upload-templates-sidebar">
          <div className="border-b border-border-subtle pb-2 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-ink-muted font-bold block">Preloaded Agreements</span>
            <span className="text-xs text-ink-muted leading-snug">Select to load sample clauses instantly for quick testing.</span>
          </div>

          <div className="space-y-3" id="template-list">
            {TEMPLATES.map((tpl, idx) => {
              const isSelected = selectedTemplateIndex === idx;
              return (
                <div
                  key={idx}
                  id={`template-card-${idx}`}
                  onClick={() => handleSelectTemplate(idx)}
                  className={`border p-4 cursor-pointer text-left transition-all relative ${
                    isSelected
                      ? 'border-accent-forest bg-accent-forest-light'
                      : 'border-border-subtle hover:bg-bg-card'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <span className="text-xs font-mono text-accent-forest uppercase tracking-wider font-semibold">
                      Template {idx + 1}
                    </span>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-accent-forest" />
                    )}
                  </div>
                  <h4 className="font-serif text-sm font-medium text-ink-dark mt-1.5 leading-snug">
                    {tpl.name}
                  </h4>
                  <p className="text-ink-muted text-xs font-sans mt-1 leading-normal">
                    {tpl.description}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="bg-bg-card p-4 border border-border-subtle text-xs text-ink-muted font-mono leading-relaxed" id="compliance-checklist">
            <span className="text-ink-dark uppercase block mb-1 font-semibold">Standard Auditing Benchmarks</span>
            <ul className="list-disc list-inside space-y-1">
              <li>Mutual NDA standard terms</li>
              <li>Enterprise SaaS vendor standards</li>
              <li>General contractor safeguards</li>
            </ul>
          </div>
        </div>

        {/* Right Side: Upload Dropzone & Paste field */}
        <form onSubmit={handleSubmit} className="lg:col-span-8 space-y-6" id="upload-form">
          
          {/* Dropzone Container */}
          <div
            id="drag-drop-zone"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-accent-forest bg-accent-forest-light'
                : 'border-border-subtle hover:bg-bg-card/40'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".txt,.md"
              className="hidden"
              id="file-input-element"
            />
            <Upload className="w-8 h-8 text-ink-muted/70 mx-auto mb-3 stroke-1" />
            <span className="text-sm font-medium text-ink-dark block">
              Drag & Drop Contract File (.txt or .md)
            </span>
            <span className="text-xs text-ink-muted font-mono uppercase tracking-wider mt-1.5 block">
              Or click to navigate file system
            </span>
            <span className="text-xs text-ink-muted font-sans mt-3 block">
              Maximum file size allowed: 5.0 MB.
            </span>
          </div>

          {/* Paste Document Text area */}
          <div className="space-y-1.5 text-left" id="paste-textbox-group">
            <div className="flex items-center justify-between" id="paste-labels">
              <label className="block text-xs font-mono uppercase tracking-wider text-ink-muted" htmlFor="contract-paste-area">
                Contract Text Editor / Paste Board
              </label>
              {docName && (
                <span className="text-xs font-mono text-accent-forest font-semibold bg-accent-forest-light px-2 py-0.5">
                  Loaded: {docName}
                </span>
              )}
            </div>
            <textarea
              id="contract-paste-area"
              rows={12}
              required
              value={inputText}
              onChange={(e) => {
                setInputText(e.target.value);
                if (selectedTemplateIndex !== null) {
                  setSelectedTemplateIndex(null);
                }
              }}
              placeholder="Paste contract clauses, draft text segments, or lease conditions directly here..."
              className="w-full bg-transparent border border-border-subtle p-4 text-sm font-sans rounded-none focus:outline-none focus:border-accent-forest transition-colors leading-relaxed"
            ></textarea>
          </div>

          {/* Optional Name field */}
          <div className="space-y-1.5 text-left" id="doc-name-textbox-group">
            <label className="block text-xs font-mono uppercase tracking-wider text-ink-muted" htmlFor="doc-name-input">
              Audit Session Reference Name
            </label>
            <input
              id="doc-name-input"
              type="text"
              value={docName}
              onChange={(e) => {
                setDocName(e.target.value);
                setSelectedTemplateIndex(null);
              }}
              placeholder="e.g. Master Service Agreement Amendment (October 2026)"
              className="w-full bg-transparent border border-border-subtle px-3 py-2 text-sm rounded-none focus:outline-none focus:border-accent-forest font-sans transition-colors"
            />
          </div>

          {/* Primary Action Button */}
          <div className="pt-2" id="upload-actions">
            <button
              id="start-audit-submit"
              type="submit"
              className="bg-accent-forest hover:bg-opacity-90 text-white font-mono text-xs tracking-wider uppercase py-3 px-6 flex items-center justify-center space-x-2 transition-all cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>Begin Legal Analysis Audit</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}

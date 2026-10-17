# PAGE_PLAN.md: Legal Analyzer App

This document outlines the complete sitemap, screen-by-screen hierarchy, real copy, and visual layout specifications for the Legal Analyzer web application.

---

## Screen 1: Landing Page (`/`)

### Purpose
To introduce the product to founders, legal-ops professionals, and independent contractors as a serious, non-lawyer contract triage engine. Clear distinction between automated triage and legal representation.

### Layout & Visual Note
- Warm off-white background (`#FBFBF9`), flat surfaces, 1px hairline borders (`#E5E5E0`).
- No floating 3D spheres, no neon gradients, no cartoon team illustrations.
- Classical serif headline (`Playfair Display`), clean sans body (`Inter`).
- Centered reading column (`max-w-4xl`), 2-column feature comparison, and clean navigation bar.

### Navigation Header
- **Brand Wordmark:** `LEGAL ANALYZER` (Font: Serif, tracking: -0.02em, color: `#1B2A4A`).
- **Links:**
  - `DOCUMENTATION` (Link to `/docs`, text: 11px uppercase tracking-wider, muted gray).
  - `SECURITY & AUDIT` (Link to `/security`, text: 11px uppercase tracking-wider, muted gray).
  - `SIGN IN` (Link to `/login`, 11px uppercase tracking-wider).
  - `START TRIAGE` (Button: Primary deep navy `#1B2A4A`, white text, 1px border, 0px radius).

### Section 1.1: Hero Section
- **Eyebrow:** `AI-ASSISTED CONTRACT TRIAGE • FOR FOUNDERS & IN-HOUSE TEAMS`
- **Headline:** First-pass contract intelligence before partner review.
- **Subheadline:** Extract clauses, flag severe indemnification risks, verify statutory governing law, and generate structured executive memorandums in minutes.
- **CTAs:**
  - Primary Button: `UPLOAD CONTRACT FOR REVIEW` (Points to `/signup`).
  - Secondary Button: `EXPLORE SAMPLE AUDIT (PDF)` (Points to `/documents/demo`).
- **Trust Banner:** `PROCESSED LOCALLY & SECURED WITH STRICT ROLE-BASED ACCESS CONTROLS` (11px, muted ink).

### Section 1.2: The Core Workflow (3-Step Hairline Grid)
- **Step 1: Ingestion & OCR**
  - *Title:* Structured Extraction
  - *Copy:* Native PDF parsing with automatic Tesseract fallback for scanned agreements. Chunks text while preserving document structure and line numbering.
- **Step 2: Clause & Risk Triage**
  - *Title:* Clause Risk Auditing
  - *Copy:* LLM evaluation against standard bilateral norms. Highlights one-sided limitation of liability, non-compete clauses, and jurisdiction anomalies.
- **Step 3: Executive Reporting**
  - *Title:* Formal Memorandum Export
  - *Copy:* Clean, printable memorandum report summarizing key obligations, deal terms matrix, risk severity distributions, and suggested redlines.

### Section 1.3: Interactive Split-Pane Demonstration Mockup
- Visual presentation of the split-pane review interface: Source document on the left, flagged risk cards with confidence badges (`CONFIDENCE: 94%`) on the right.
- Highlighting actual contract text excerpt: *"In no event shall Provider's total aggregate liability exceed the fees paid in the prior one (1) month..."* flagged with crimson high-risk badge: `LIABILITY CAP TOO RESTRICTIVE`.

### Section 1.4: Mandatory Statutory Disclaimer Banner
- Full-width box with 1px border (`#E5E5E0`) and background `#FFFFFF`.
- **Text:** *"Legal Analyzer is an AI-powered software application designed to assist legal professionals, business founders, and contracting parties in conducting preliminary document triage. Legal Analyzer does not practice law, does not offer legal opinions, and does not establish an attorney-client relationship. All findings, severity ratings, and clause identifications must be reviewed and verified by a licensed attorney before signing or executing any legal instrument."*

---

## Screen 2: Authentication (`/login` & `/signup`)

### Purpose
Secure access via Supabase Auth. Minimalist, distraction-free credential entry with security attestation.

### Layout & Visual Note
- Centered 420px wide card with 1px hairline border, white surface, zero drop-shadow.
- Serif title, sharp input boxes with subtle borders, primary deep navy submit button.

### Real Copy (`/login`)
- **Title:** Sign in to Legal Analyzer
- **Subtitle:** Enter your credentials to access your document repository and triage audit history.
- **Input 1 Label:** Work Email Address
- **Input 1 Placeholder:** `counsel@company.com`
- **Input 2 Label:** Password
- **Submit Button:** `AUTHENTICATE & ENTER`
- **Footer Link:** `Need an account? Request Workspace Access`

### Real Copy (`/signup`)
- **Title:** Create Workspace Account
- **Subtitle:** Register your team to begin uploading contracts, NDAs, and commercial agreements.
- **Input 1 Label:** Full Name
- **Input 2 Label:** Work Email Address
- **Input 3 Label:** Choose Password (Minimum 10 characters)
- **Checkbox:** *"I acknowledge that Legal Analyzer provides assistive triage and does not provide legal advice."*
- **Submit Button:** `CREATE ACCOUNT`

---

## Screen 3: Central Dashboard (`/dashboard`)

### Purpose
Repository view of all uploaded contracts, showing processing status, risk ratings, safety scores, and quick navigation.

### Layout & Visual Note
- Sticky top navigation bar with user profile and upload CTA.
- Top metrics summary row: 4 key performance cards (Total Documents, High Risk Flagged, In Processing, Completed).
- Filter and search controls bar: search by filename, filter by status (All, Completed, Processing, Failed), filter by risk (High, Medium, Low), sort by upload date.
- Primary Table: High-density legal docket table with right-aligned scores and status badges.

### Metric Cards
1. **Total Documents Ingested:** Counter (e.g. `142`), Subtitle: `Lifetime workspace repository`.
2. **High Risk Provisions:** Counter (e.g. `18`), Subtitle: `Immediate counsel escalation recommended`.
3. **Active Pipelines:** Counter (e.g. `2`), Subtitle: `OCR & LLM analysis underway`.
4. **Average Safety Index:** Counter (e.g. `78/100`), Subtitle: `Standard commercial benchmark`.

### Docket Table Columns
- **Document Identifier & Name:** e.g. `Master Services Agreement - Acme Corp (v3.2).pdf`
- **Document Type:** `NDA` | `SaaS Terms` | `Employment` | `Vendor Agreement`
- **Uploaded Date:** `Oct 14, 2026 • 14:32 UTC`
- **Status:** Badge (`COMPLETED`, `PROCESSING`, `FAILED`)
- **Safety Score:** Right-aligned numeric rating (e.g. `64 / 100`)
- **Risk Rating:** Badge (`HIGH RISK`, `MEDIUM RISK`, `LOW RISK`)
- **Action:** `OPEN INSPECTOR` (Link to `/documents/[id]`)

### Empty State (When no documents exist)
- Bordered container with subtle background:
- *Headline:* `No contracts currently under review`
- *Body:* `Upload a contract, NDA, or policy agreement in PDF or DOCX format to initiate OCR extraction and clause risk scoring.`
- *Button:* `UPLOAD FIRST DOCUMENT`

---

## Screen 4: Document Upload View (`/documents/upload`)

### Purpose
Drag-and-drop zone with strict file validation, supported format specifications, and processing settings.

### Layout & Visual Note
- Centered 680px container.
- Large upload dropzone with 1px dashed hairline border (`border-dashed border-[var(--border-subtle)]`).
- Background changes subtly on drag-hover to `#F4F4F0`.

### Real Copy
- **Header:** Ingest New Legal Document
- **Dropzone Title:** Drag and drop your contract here, or browse files
- **Format Requirements:** `Supported formats: PDF, DOCX (Up to 25 MB). OCR automatically activated for scanned files.`
- **Configuration Toggle:**
  - Label: `Jurisdiction Benchmark`
  - Options: `United States (Delaware / Federal)`, `United Kingdom (England & Wales)`, `General Common Law`
- **Security Confirmation:** `All files encrypted in transit and at rest. Text extraction logs are scrubbed according to enterprise retention policy.`
- **Submit Button:** `START AUTOMATED TRIAGE`

---

## Screen 5: Interactive Split-Pane Review (`/documents/[id]`)

### Purpose
The primary workhorse of the application. Allows legal reviewers and founders to inspect original extracted text on the left, synchronized with structured clause auditing, deal terms, and redline recommendations on the right.

### Layout & Visual Note
- Dual-pane layout: 50% left pane for extracted source text, 50% right pane with tabbed analysis components.
- On tablet / mobile: Stacks into responsive toggle tabs (`[Source Document]` | `[Risk Analysis]` | `[Deal Terms]`).
- Left pane features line-numbered contract text with highlighted clauses. Clicking a clause scrolls the audit card into view, and vice versa.

### Right Pane Tabs
1. **Clause Audit (Default):**
   - Summary Card: Document Overview, Parties Identified, Governing Law, Safety Score (`72 / 100`).
   - Risk Clause Cards:
     - Card 1: `Indemnification Clause` • Risk: `HIGH` • Explanation: *"Uncapped unilateral indemnity requiring Customer to defend all third-party intellectual property claims without mutual obligation."*
     - Card 2: `Non-Compete Covenant` • Risk: `MEDIUM` • Explanation: *"24-month duration extends beyond standard 12-month commercial enforceability guidelines."*
     - Card 3: `Governing Law & Jurisdiction` • Risk: `LOW` • Explanation: *"State of Delaware, standard commercial arbitration venue."*
2. **Deal Terms Matrix:**
   - Structured tabular comparison of critical commercial levers (Term Duration, Liability Cap, Payment Terms, Termination for Convenience).
3. **Redline Workbench:**
   - Suggested counter-proposals with standard bilateral wording replacements.
4. **Document Chat Drawer:**
   - Interactive inquiry drawer allowing questions against the verified text chunks (e.g. *"Does this contract automatically renew?"*).

---

## Screen 6: Executive Memorandum Report (`/reports/[id]`)

### Purpose
Clean, printable memorandum layout formatted specifically for executive sign-off, internal deal files, or external lawyer handoff.

### Layout & Visual Note
- White paper surface (`#FFFFFF`) with print-optimized CSS (`@media print`).
- Formal memo header: `TO:`, `FROM: Legal Analyzer Automated Triage Engine`, `DATE:`, `RE: Contract Review Memorandum`.
- Right-aligned export buttons: `EXPORT AS PDF` and `COPY SHAREABLE LINK`.

### Content Sections
1. **Memorandum Header:** Document metadata, upload hash, model version, timestamp.
2. **Executive Summary:** Plain-English summary of agreement purpose, key counterparties, and effective dates.
3. **Risk Exposure Summary:** Visual risk count tally (High / Medium / Low) with overall safety score.
4. **Critical Clause Breakdown:** Full list of flagged clauses with verbatim quote, statutory reasoning, and remediation notes.
5. **Missing Standard Clauses:** Flags missing boilerplate or safety clauses (e.g. Force Majeure, Severability, Mutual Confidentiality).
6. **Signature & Legal Disclaimer:** Mandatory attestation box noting that this memo serves as triage assistance, not a legal opinion.

---

## Screen 7: Admin Audit Log & Governance (`/admin`)

### Purpose
System transparency and enterprise compliance tracking. Every document upload, view, analysis, export, or deletion generates an immutable audit record.

### Layout & Visual Note
- Full-width data table view.
- Monospace IDs and timestamps.
- Action filter: `All Actions`, `UPLOAD`, `VIEW`, `ANALYZE`, `EXPORT`, `DELETE`.

### Audit Table Columns
- **Timestamp (UTC):** `2026-10-17 12:45:12`
- **User / Operator:** `counsel@company.com`
- **Action Type:** `DOCUMENT_EXPORT`
- **Document Reference ID:** `doc_88f91c3e`
- **IP Address & Agent:** `192.168.1.45 (Next.js SSR)`
- **Status:** `SUCCESS (200)`

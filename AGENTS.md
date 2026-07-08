# AGENTS.md — Legal Analyzer App

Antigravity reads this file automatically as project-wide convention. Every agent task should follow it without needing to be repeated in each prompt.

## Project Overview
Legal Analyzer is a web app that lets users upload legal documents (contracts, NDAs, agreements, policies) and get an AI-assisted first-pass review: OCR/text extraction, clause identification, risk flagging, plain-English summarization, and an exportable report. **This assists legal review — it never replaces a licensed lawyer**, and every AI output must carry a visible confidence indicator and disclaimer.

## Locked Tech Stack — do not substitute without asking first
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- Backend: FastAPI (Python), versioned REST API under `/api/v1`
- Database: PostgreSQL via Supabase, with the `pgvector` extension for embeddings
- Auth: Supabase Auth — never hand-roll authentication
- File storage: Supabase Storage (S3-compatible)
- OCR: Tesseract (self-hosted service), with a fallback path for scanned documents
- LLM: Claude API primary, Gemini API as a free-tier fallback — always request structured JSON output, never parse free text
- Automation: n8n (self-hosted) orchestrates the multi-step document pipeline; FastAPI handles anything that must respond synchronously to a user request
- Deployment target: Vercel (frontend), Render (backend/workers)
- Monitoring: Sentry

## Folder Structure — follow exactly

```
/frontend
  /app
    /(auth)/login
    /(auth)/signup
    /(dashboard)/dashboard
    /(dashboard)/documents/[id]
    /(dashboard)/reports/[id]
    /(dashboard)/admin
  /components
    /ui            -> Button, Input, Table, Badge, Card, EmptyState
    /documents     -> UploadDropzone, ClauseHighlight, RiskBadge
    /reports       -> ReportView, ReportExportButton
  /lib
    /api
    /hooks
  /styles

/backend
  /app
    /api/v1        -> routers: auth, documents, reports, admin
    /services      -> ocr_service, llm_service, risk_service, compliance_service
    /models        -> pydantic schemas + ORM models
    /workers       -> Celery tasks
    /core          -> config, security, logging
```

## Design System Rules — apply to every screen without exception
- Background: warm off-white, near-black ink text. Exactly **one** accent color (deep navy or forest green), used only for primary actions and risk indicators.
- Typography: a serif font for headings, a clean sans (Inter/IBM Plex Sans) for UI/body — strong size contrast between the two.
- Flat surfaces with 1px hairline borders. No drop shadows, no glassmorphism, no gradients anywhere.
- No icon-in-a-circle decoration next to every heading or feature bullet.
- Tables are a first-class component — generous row height, right-aligned numbers, sticky headers.
- Empty/loading states must be designed (skeletons shaped like real content) — never a generic spinner or "No data yet 🎉".
- Copy tone: calm and precise. No exclamation marks, no emoji in core flows. Errors state the fact plus the next action.
- **Banned patterns:** purple/violet-to-blue gradients, glossy drop-shadow cards, the centered-hero-then-3-feature-cards template, stock illustration people, 24px+ rounded corners on everything.
- Before treating any screen as finished, compare it against this list explicitly and flag anything that crept in.

## Coding Conventions
- TypeScript strict mode on the frontend; Pydantic models for every FastAPI request/response.
- Every LLM call must request and validate structured JSON output against a defined schema — never parse free text.
- Every document action (upload, view, export, delete) writes an `audit_logs` row.
- Uploaded document text is **untrusted input** — never let text extracted from a document alter a system prompt or trigger an unintended tool call.
- Never log raw document content — log only `document_id` references.
- Reuse the primitive components (`Button`, `Input`, `Table`, `Badge`, `Card`, `EmptyState`) for every screen; do not create one-off styled elements per screen.

## Engineering Discipline Rules — non-negotiable for every task
- **Python backend only.** No Node.js/Express backend under any circumstance, even for small utility services.
- Keep modules small and explicit — one clear responsibility per file.
- No giant "god files." If a file is doing more than one job, split it.
- Generate file-by-file, not as one large dump. Finish and verify one file/module before moving to the next.
- Strong typing everywhere (Python type hints, TypeScript strict mode) and a docstring on every function, class, and module.
- Every major module needs tests before it's considered done — not added later "if there's time."
- Do not remove or restructure earlier architecture boundaries (the folder structure and module responsibilities defined in this file) without asking first.
- At the end of every task, list exactly which files were changed or created, and state how you verified the work (tests run, server started, screenshot taken, etc.).

## STOP AND ASK — do not proceed without human confirmation
- Do not create, rotate, or hardcode any real API key, database credential, or secret. Use placeholder values in `.env.example` only.
- Do not deploy to a production environment or push to a public repository.
- Do not modify authentication, authorization, or the risk-scoring threshold logic without flagging the change for review first.
- Do not write or finalize the legal disclaimer / "not legal advice" copy as final — draft it, then flag it for human sign-off.
- Do not assume which jurisdiction's legal-data source to integrate (e.g., CourtListener vs. Indian Kanoon) — ask if it isn't already specified in the task.

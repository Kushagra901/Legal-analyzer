# Legal Analyzer — Complete Project Audit

**Audit date:** 18 September 2026  
**Scope:** 123 tracked repository files. This includes backend and frontend source, migrations, configuration, CI, Docker/n8n workflow, documentation, tests, generated configuration, and sample-document metadata. Sample contracts were not read because uploaded legal content is untrusted and potentially sensitive. Generated lockfiles were inventoried but not manually reviewed line-by-line.

## Executive Assessment

Legal Analyzer is a feature-rich MVP with a practical first-pass review workflow: uploads, native text extraction with OCR fallback, clause/risk analysis, report export, RAG-style document chat, deep extraction, redline suggestions, review decisions, audit events, and an n8n workflow.

It is **not production-ready**. The current release has three blocking categories: authentication/authorization, migration and workflow reliability, and legal-AI evidence controls. Resolve P0 issues before accepting real customer documents.

## Files Reviewed

| Area | Files reviewed | Result |
|---|---:|---|
| Backend application, services, workers, models, routes | 31 | Core capability exists; security, ownership, and job-idempotency gaps remain. |
| Backend migrations, scripts, Docker, dependencies, examples | 16 | Conflicting migration paths and deployment/runtime gaps found. |
| Backend test modules | 18 | 113 tests collected; backend coverage is substantial but misses critical production paths. |
| Frontend routes, components, UI primitives, API/auth helpers | 36 | Strong visual foundation; several API-contract and production-routing defects found. |
| Frontend configuration, docs, static assets | 14 | Production configuration and documentation are incomplete/stale. |
| Root CI, Docker, n8n, scripts, docs, metadata, examples | 8 | Local development support is useful; production orchestration is incomplete. |

## What Is Already Good

- Clear stack alignment: Next.js App Router, TypeScript, FastAPI, PostgreSQL/Supabase, pgvector, Celery, n8n, and Sentry.
- Upload size limits, MIME allowlist, rate limiting, security headers, document ownership checks, and several focused backend tests already exist.
- AI services use layered fallbacks and prompt-injection delimiters. Chat retrieval is explicitly scoped to a document ID.
- The UI mostly follows the intended legal-tech design language: calm palette, serif headings, flat bordered cards, tables, skeleton states, and no gradients.
- Report generation supports PDF and DOCX, while the document workspace contains chat, clause review, deal-term, and redline views.
- Tests cover OCR formats, fallback behavior, document chat isolation, reports, review decisions, rate limiting, and many service behaviors.

## P0 — Must Fix Before Production

### 1. Authentication fallback can accept arbitrary bearer tokens

`backend/app/core/auth.py` treats any bearer token as the local mock user whenever Supabase is not configured. A misconfigured deployment could therefore expose authenticated API access without a valid session. The internal-token path also creates a universal administrator principal.

**Required decision and fix:** add an explicit environment mode, allow the mock token only in development/test, fail production startup if Supabase configuration is absent, and restrict internal service access to private networking plus a rotated secret. This changes authentication/authorization and requires owner approval.

### 2. Database tables are broadly granted without row-level security

`backend/migrations/0001_initial_schema.sql` grants `anon` and `authenticated` read/write access to business tables but defines no RLS policies. If Supabase Data API access is enabled, FastAPI ownership checks can be bypassed.

**Required decision and fix:** enable RLS on every exposed table and use policies based on `auth.uid()` and organization membership. Remove broad grants that are not required. This changes authorization and requires owner approval.

### 3. Database migration path can fail on a fresh environment

`backend/migrate.py` reruns every SQL file with no migration ledger. Migrations `0005_add_chat_messages.sql` and `0007_add_document_chunks_and_chat_messages.sql` both create `chat_messages` with incompatible constraints, while one creates duplicate indexes without idempotency. There is also an isolated Alembic revision without Alembic tooling or a revision chain.

**Required fix:** choose one migration tool, establish version tracking, reconcile the duplicate table definition, test a clean database bootstrap, then baseline an existing shared environment in staging before production.

### 4. Two pipelines can process the same document concurrently

Upload dispatches Celery or a FastAPI background task and separately triggers n8n. The n8n workflow invokes OCR, agent analysis, standard analysis, score, compliance, report, extraction, audit, and escalation endpoints. This can race, overwrite status, duplicate clauses, duplicate analysis records, and send contradictory results.

**Required fix:** choose one orchestration owner per step; use `automation_runs` as an actual idempotency ledger; give jobs correlation IDs and explicit state transitions; prohibit overlapping analysis runs for a document.

### 5. AI output is not consistently evidence-bound or schema-validated

The Claude path strips Markdown fences and parses free-form text with `json.loads`, which conflicts with the project rule that LLM output must be validated structured JSON. Main document results do not consistently present source coordinates, per-finding confidence, or an abstention state. The frontend receives confidence in chat/deep extraction responses but does not consistently render it.

**Required fix:** use provider-native structured outputs where available; validate against Pydantic models; store source clause/page references; show confidence and a visible evidence/abstain state for every generated finding. Legal disclaimer wording requires human sign-off before finalization.

## P1 — High-Priority Functional and Security Gaps

### File handling, storage, and privacy

- Upload validation trusts declared MIME type or extension; it needs magic-byte/content-signature verification, archive limits, image/PDF page limits, and malware scanning.
- The `documents` table has no storage path. Delete removes database rows but cannot reliably delete the uploaded original or exported reports, creating a retention and privacy failure.
- Report export calls a public URL helper even though the bucket is created private. Use short-lived signed URLs and persist object keys.
- External AI providers receive extracted text without optional PII masking, consent controls, retention configuration, or a data-processing audit record.
- User-supplied audit actions and review notes can be written verbatim to `audit_logs`, conflicting with the rule that raw document content must not be logged.

### API and workflow behavior

- `POST /ocr` only returns a status and does not perform OCR. The n8n workflow calls it as if it does.
- `/analyze` and `/agent-analyze` can analyze the string `Sample contract text.` when extraction is unavailable, creating fabricated results instead of a clear failed/manual-review state.
- The background worker always runs `standard_nda` compliance, ignoring detected document type or user policy.
- Re-running the worker does not clear prior clauses, flags, compliance records, or references before inserting new rows.
- Status values are inconsistent (`processing`, `completed`, `analyzed`, `escalated`); dashboard metrics only count selected values and can misrepresent workload.
- `/report` stores a placeholder report URL instead of generating the export, while a different route performs generation; users and workflow nodes can receive an invalid report link.
- Invalid chat conversation UUIDs raise a server error instead of a request validation error.
- Error responses expose exception messages in several routes, leaking implementation details to clients.

### Tenant and audit model

- New Supabase users are assigned to the first available organization, not a defined tenant onboarding flow.
- Backend document access is user-scoped, not organization-scoped. Administrator access is global and audit logs lack an actor/user ID.
- Required audit coverage is incomplete for status views, chat-history reads, review-list reads, and report downloads. Deleting document-linked audit logs also weakens the audit trail.
- `ensure_test_user_exists` contains production database mutation logic for a fixed test identity and should be test-only or removed.

### Frontend/API contract defects

- Backend admin responses use `timestamp` and `user`; frontend typing expects `created_at` and omits `user`, so timestamps do not render reliably.
- `updateClause` only posts an audit event; it does not update a clause. The API name implies functionality that does not exist.
- `useDocumentList` is an unused placeholder returning an empty list and `loading: false`.
- The document chat UI saves confidence but does not display it; several AI results likewise lack visible confidence/evidence.
- Chat failure is only logged to the console; no designed inline error/retry state is shown.
- `ErrorBoundary` shows raw runtime exception messages to users.

### Deployment and operations

- `frontend/next.config.ts` rewrites to `localhost:8000`, which fails from Vercel unless every browser call supplies an absolute API URL. Make the backend URL environment-driven for server rewrites and validate it at build/deploy time.
- `docker-compose.yml` lacks frontend, Redis, and worker services, while the app expects Redis/Celery. Its external n8n volume must already exist.
- n8n references `host.docker.internal` and `localhost` dashboard URLs, which are unsuitable for Linux/Render production hosts and email recipients.
- The workflow does not provide the described n8n error-trigger/retry workflow, durable step-level idempotency, or an environment-aware public dashboard URL.
- CI builds the frontend but does not run frontend lint or tests. Dependency audit covers pip only, not npm.
- Backend dependencies are broad unpinned ranges; no lockfile is present for Python, while `backend/package-lock.json` is unrelated and empty.
- Application logging is configured but not initialized; many production paths use `print` and can include raw exception details.

## P2 — Quality, Maintainability, and UX Improvements

- Split the 54 KB `documents.py` router into upload, analysis, review, chat, and lifecycle modules.
- Replace hard-coded hex styles and raw HTML controls in feature components with the existing UI primitives and CSS variables.
- Replace `any` types in frontend response contracts with generated OpenAPI types or shared schema types.
- Remove placeholder backend `/auth/login` and `/auth/signup` endpoints, or make them real Supabase-compatible flows. The frontend authenticates directly with Supabase, creating an ambiguous API surface.
- Replace the boilerplate frontend README and missing screenshot/`docs` references in the root README. Replace placeholder GitHub badge URLs.
- Remove unused default Next/Vercel SVG assets, stale `CLAUDE.md`, empty `openapi.json`, and dead helper code after confirming no dependency.
- Reconcile the architecture document with implementation: it describes real auth, OCR routing, error workflow, signed URLs, citation traceability, and production safety controls that are not currently complete.
- The landing page uses the banned centered-hero plus feature-card pattern. Some screens also use emoji, raw alerts, generic pulse blocks, and one-off styles contrary to the project design rules.

## Test and Validation Assessment

- `pytest --collect-only -q` found **113 backend tests** across 18 modules.
- Backend `ruff check` passed during the audit. Focused suites for agent analysis, asynchronous status, document chat, and migration-adjacent behavior were exercised successfully.
- The desktop test command did not return a complete whole-suite summary within its execution window; full CI verification is still required before release.
- Frontend `npm run lint` and `npm run build` completed during the audit.
- Missing tests: authentication production mode, RLS policies, object deletion/retention, MIME spoofing/malware limits, concurrent job idempotency, n8n behavior, browser upload-to-report flow, accessibility, responsive behavior, and frontend API contract validation.

## Product Roadmap — Differentiators Worth Building

1. **Organization playbooks:** configurable approved positions for liability caps, governing law, notice periods, and data-processing terms.
2. **Evidence-first review:** every risk finding links to exact PDF page/coordinates, source text, confidence, and the policy rule it violates.
3. **Revision intelligence:** compare two versions semantically, rank meaningful changes, and produce a negotiation-ready change summary.
4. **Obligation calendar:** turn dates, renewals, cure windows, notices, and payment milestones into assigned tasks and ICS exports.
5. **Negotiation pack:** export counsel-reviewable fallback language with rationale, deal impact, source citation, and approval history.
6. **Privacy modes:** per-document provider selection, PII redaction, no-retention option, and legal-hold/deletion workflow.
7. **Portfolio analytics:** identify recurring vendor deviations, renewal exposure, top risk categories, and review turnaround without exposing document text.
8. **Human review queue:** assign reviewers, require approval before external export/escalation, and retain immutable decision history.
9. **Jurisdiction packs:** only after a jurisdiction is chosen, add attorney-approved sources and policy templates rather than generic legal citations.

## Recommended Delivery Order

1. Obtain approval for authentication and RLS remediation.
2. Consolidate migrations and prove clean database bootstrap in staging.
3. Make one idempotent orchestration pipeline with explicit state transitions.
4. Add storage object keys, signed URLs, deletion/retention controls, MIME signature checks, page limits, and malware scanning.
5. Enforce structured AI schema validation, evidence references, confidence display, and human-review gates.
6. Fix API/frontend contract mismatches and add browser-level end-to-end tests.
7. Complete production deployment configuration, observability, runbooks, backups, and CI quality gates.
8. Build playbooks, version comparison, obligation calendar, and portfolio intelligence after the safety baseline is complete.

## Non-Code Audit Note

The app currently contains multiple variants of the legal-review disclaimer. Do not finalize or standardize this language without qualified human review and sign-off.

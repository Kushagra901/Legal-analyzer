# Legal Analyzer

**AI-assisted first-pass review for contracts, NDAs, and legal documents — extraction, risk flagging, and reporting in minutes, not days.**

![Build Status](https://img.shields.io/github/actions/workflow/status/your-username/legal-analyzer/ci.yml?branch=main)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Release](https://img.shields.io/badge/release-v0.1.0--alpha-orange)
![Repo Size](https://img.shields.io/github/repo-size/your-username/legal-analyzer)
![Languages](https://img.shields.io/badge/stack-Python%20%7C%20TypeScript-informational)

*Assumption: badge URLs use a placeholder path `your-username/legal-analyzer` — swap in your real GitHub path once the repo is live.*

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Demo / Screenshots](#demo--screenshots)
- [Quick Start](#quick-start-install--run)
- [Detailed Usage](#detailed-usage)
- [Configuration & Environment](#configuration--environment)
- [Architecture & File Structure](#architecture--file-structure)
- [Data Model / Schema](#data-model--schema)
- [Tests](#tests)
- [CI/CD](#cicd)
- [Deployment](#deployment)
- [Security & Secrets](#security--secrets)
- [Performance & Scaling](#performance--scaling)
- [Logging & Monitoring](#logging--monitoring)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Maintainers & Contact](#maintainers--contact)
- [License](#license)
- [Acknowledgements & Credits](#acknowledgements--credits)
- [Appendix](#appendix)

## Overview

Legal Analyzer lets a user upload a contract, NDA, or policy document and get an AI-assisted first-pass review back: extracted clauses, risk flags with severity, a plain-English summary, and an exportable report. It's built for founders, freelancers, and small teams who need a fast triage step before — not instead of — real legal review.

The system is a two-service architecture: a **Next.js** frontend and a **FastAPI** backend, connected through a versioned REST API. Documents are stored in object storage, text is extracted and chunked, an LLM performs clause/risk analysis with structured JSON output, and results are persisted to Postgres (or local SQLite in development) for the dashboard and report views.

This is an active MVP, not a finished product — several pieces (real OCR, real auth, automation) are intentionally mocked or stubbed right now. See [Roadmap](#roadmap) for what's next.

## Key Features

- Document upload with file-type and size validation
- Text extraction from native PDFs, with a scanned-document fallback path
- LLM-based clause extraction, risk scoring, and plain-English summarization
- Structured JSON output validated against a schema — no free-text parsing
- Interactive document viewer: click a flagged clause to highlight and scroll to it in the source text
- Clean, printable memorandum-style report export
- Full audit logging of every document action
- Database auto-switching: SQLite locally, Postgres/Supabase in production, zero config changes
- Admin view of audit logs

## Demo / Screenshots

Run the stack locally, then open the dashboard and upload a sample file:
```bash
docker compose up --build
# then visit http://localhost:3000 and upload a PDF from /test-documents
```
- **Dashboard** — document list with status and risk level per row *(screenshot placeholder)*
- **Document view** — split pane, source text with clickable clause highlights *(screenshot placeholder)*
- **Report view** — printable memorandum layout *(screenshot placeholder)*

## Quick Start (Install & Run)

**Prerequisites:** Node.js 20+, Python 3.11+, Git. Docker optional but recommended.

### Unix / macOS
```bash
git clone https://github.com/your-username/legal-analyzer.git
cd legal-analyzer/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000 &

cd ../frontend
npm install
cp .env.example .env.local
npm run dev
```

### Windows (PowerShell)
```powershell
git clone https://github.com/your-username/legal-analyzer.git
cd legal-analyzer\backend
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
Start-Process uvicorn app.main:app --reload --port 8000

cd ..\frontend
npm install
copy .env.example .env.local
npm run dev
```

Visit `http://localhost:3000`. **Important:** without a `GEMINI_API_KEY` set, analysis falls back to an offline rule-based parser — fine for exploring the UI, not representative of real output quality.

## Detailed Usage

**Upload and analyze a document (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <mock-or-real-token>" \
  -F "file=@sample_nda.pdf"
```

**Example JSON response:**
```json
{
  "document_id": "3f1c2e4a-...",
  "status": "processing",
  "filename": "sample_nda.pdf"
}
```

**Fetch results:**
```bash
curl http://localhost:8000/api/v1/documents/3f1c2e4a-...
```

**Postman:** import `POST {{base_url}}/api/v1/documents` as a `multipart/form-data` request with a `file` key, and set `base_url = http://localhost:8000`.

## Configuration & Environment

| Variable | Service | Required | Default / Notes |
|---|---|---|---|
| `DATABASE_URL` | backend | No | Omit for local SQLite (`legal.db`); set for Postgres/Supabase |
| `GEMINI_API_KEY` | backend | No | Enables real LLM analysis; falls back to rule-based parsing without it |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | backend, frontend | No (yet) | Needed once mock auth is replaced with real Supabase Auth |
| `AUTH_MOCK_TOKEN` | backend | No | Local-dev-only token accepted by the mock auth layer |
| `SENTRY_DSN` | backend, frontend | No | Error monitoring in staging/production |
| `NEXT_PUBLIC_API_URL` | frontend | **Yes** | e.g. `http://localhost:8000` |

Default ports: backend `8000`, frontend `3000`. Production recommendation: set `DATABASE_URL`, `GEMINI_API_KEY`, and `SENTRY_DSN` explicitly; never rely on fallback defaults outside local development.

## Architecture & File Structure

```
/frontend/app          -> routes: (auth), (dashboard)/{dashboard,documents/[id],reports/[id],admin}
/frontend/components    -> ui/ (primitives), documents/, reports/
/backend/app/api/v1     -> routers: auth, documents, reports, admin
/backend/app/services   -> ocr_service, llm_service, risk_service, compliance_service
/backend/app/models     -> SQLAlchemy models + Pydantic schemas
/backend/app/core       -> config, database, security, logging
/docs                   -> architecture and design documentation
```
Request flow: frontend → FastAPI → Postgres/SQLite, with document processing (OCR → LLM → risk scoring) run as a background step, not inline on the request.

## Data Model / Schema

| Entity | Key Fields |
|---|---|
| `users` | id, org_id, email, role |
| `organizations` | id, name, plan |
| `documents` | id, user_id, filename, status |
| `extracted_text` | id, document_id, content, method |
| `clauses` | id, document_id, clause_type, clause_text |
| `risk_flags` | id, clause_id, severity, explanation |
| `compliance_checks` | id, document_id, rule_set, result |
| `reports` | id, document_id, format, file_url |
| `audit_logs` | id, document_id, action, created_at |

Full schema and ER diagram: [`docs/legal-analyzer-architecture.md`](./docs/legal-analyzer-architecture.md#section-7--database-schema).

## Tests

```bash
cd backend && ruff check . && pytest --cov=app --cov-report=term-missing
cd frontend && npm run lint && npm test
```
Recommended coverage target: **80%** on backend services (`ocr_service`, `llm_service`, `risk_service`), lower priority on UI components.

## CI/CD

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  lint-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt && cd backend && ruff check .
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt && cd backend && pytest
  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm install && npm run lint
```

## Deployment

*Assumption: this project targets Vercel + Render (both free-tier friendly) rather than Heroku/GCP/AWS, matching the stack already chosen in `docs/legal-analyzer-architecture.md`.*

**Local Docker:**
```bash
docker compose up --build
```

**Production:**
1. Frontend → **Vercel** (connect the GitHub repo, auto-deploys on push to `main`)
2. Backend → **Render** (Docker web service, set env vars in the Render dashboard)
3. Database → **Supabase** (managed Postgres + pgvector)

Recommended production strategy: containerized backend + managed Postgres + secrets stored in the hosting provider's environment-variable manager — never in the repo.

## Security & Secrets

- Store secrets only in `.env` (local, gitignored) or your host's secret manager — never in code or client bundles.
- Run `pip-audit` and `npm audit` before each release to scan for known vulnerabilities.
- **Hardening basics:** restrict CORS to known frontend origins, rate-limit the upload endpoint, validate file type/size server-side (not just in the UI), and treat all extracted document text as untrusted input.

## Performance & Scaling

- Profile slow endpoints with `py-spy` or FastAPI's built-in timing middleware before optimizing blindly.
- Cache repeated embeddings and LLM system prompts to cut redundant API calls.
- Scale horizontally by separating the API from the OCR/LLM worker process — the worker is the bottleneck, not the API layer.

## Logging & Monitoring

- Log levels: `INFO` for request lifecycle, `WARNING` for fallback paths triggered (e.g., mock LLM used), `ERROR` for failures needing attention.
- Example structured log:
```json
{"level": "INFO", "event": "document_processed", "document_id": "3f1c2e4a", "duration_ms": 842}
```
- Monitoring: **Sentry** for error tracking; Prometheus/Grafana recommended once traffic justifies the added ops overhead.

## Troubleshooting / FAQ

1. **Backend won't start / `ModuleNotFoundError`** — activate the virtualenv and re-run `pip install -r requirements.txt`.
2. **Frontend can't reach the API** — check `NEXT_PUBLIC_API_URL` matches the backend's actual port.
3. **Analysis always returns generic results** — `GEMINI_API_KEY` is likely unset; you're on the offline fallback parser.
4. **SQLite file locked errors** — stop any second process (e.g. a stray `uvicorn --reload` instance) accessing `legal.db`.
5. **CORS errors in the browser console** — add your frontend origin to the backend's allowed-origins list.
6. **Upload succeeds but status never updates** — check the backend logs for a failed background task; the current MVP processes synchronously, so a hung request usually means an unhandled exception in `llm_service`.

## Contributing

- Code style: `ruff format` (Python), `prettier` + `eslint` (TypeScript) — run both before committing.
- Commit convention: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`).
- Branch strategy: `main` is always deployable; branch as `feature/<short-name>` or `fix/<short-name>`.
- **PR checklist:** tests pass locally, no secrets in the diff, linked to an issue if one exists, screenshots included for UI changes.

## Roadmap

1. Replace mock auth with real Supabase Auth
2. Replace OCR fallback with real Tesseract integration
3. Add compliance-check rule engine
4. Add jurisdiction-specific legal citation lookup
5. Build n8n automation pipeline with retries and human-review escalation
6. Add admin dashboard and multi-org support
7. Add automated test coverage for frontend components
8. Move background processing off the request thread into a proper task queue

## Maintainers & Contact

**Primary maintainer:** your-name (`your-email@example.com`). For urgent issues, open a GitHub Issue tagged `urgent` — response times aren't guaranteed on a solo/learning project.

*Assumption: maintainer contact is a placeholder — replace with your real name and a monitored email or GitHub handle.*

## License

**MIT License** — chosen because it's the most permissive common option for a learning/portfolio project, allowing others to freely use and build on the code with minimal friction, while you retain attribution.

## Acknowledgements & Credits

Built with [Next.js](https://nextjs.org), [FastAPI](https://fastapi.tiangolo.com), [SQLAlchemy](https://www.sqlalchemy.org), [Tailwind CSS](https://tailwindcss.com), [shadcn/ui](https://ui.shadcn.com), [pypdf](https://pypdf.readthedocs.io), and the [Gemini API](https://ai.google.dev). Automation designed around [n8n](https://n8n.io).

## Appendix

- Architecture & schema: [`docs/legal-analyzer-architecture.md`](./docs/legal-analyzer-architecture.md)
- Design system & build order: [`docs/legal-analyzer-execution-blueprint.md`](./docs/legal-analyzer-execution-blueprint.md)
- AI agent conventions: [`AGENTS.md`](./AGENTS.md)

**Command summary:**
```bash
uvicorn app.main:app --reload --port 8000   # backend
npm run dev                                  # frontend
ruff check . && pytest                       # backend tests
npm run lint && npm test                     # frontend tests
docker compose up --build                    # full local stack
```

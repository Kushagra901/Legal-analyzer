# Legal Analyzer

**AI-assisted first-pass review for contracts, NDAs, and legal documents — extraction, risk flagging, and reporting in minutes, not days.**

![Build Status](https://img.shields.io/github/actions/workflow/status/Kushagra901/Legal-analyzer/ci.yml?branch=main)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Release](https://img.shields.io/badge/release-v0.1.0--alpha-orange)
![Repo Size](https://img.shields.io/github/repo-size/Kushagra901/Legal-analyzer)
![Languages](https://img.shields.io/badge/stack-Python%20%7C%20TypeScript-informational)

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Demo & Core Views](#demo--core-views)
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
- **PySpark batch analytics** — risk distribution, clause frequency, temporal trends over the document corpus
- **Apache Kafka event streaming** — decoupled document lifecycle events (uploaded → processing → completed → failed)
- **Star schema data modelling** — dimensional model with fact tables, SCD Type 2 tracking for document re-analysis history
- **SQL window functions** — rolling averages, rank/dense_rank, LAG/LEAD, cumulative sums, NTILE quartiles via PostgreSQL analytics views
- **Lakehouse / Delta Lake architecture** — medallion pattern (Bronze → Silver → Gold) with Databricks notebook and Unity Catalog config
- **Orchestration pipelines** — Azure Data Factory JSON template + Apache Airflow DAG for the same workflow
- **MCP server** — Model Context Protocol endpoint exposing document data as LLM-queryable tools/resources
- **Data quality governance** — automated validation of text extraction, clause quality, embedding dimensions, risk score consistency
- **Multi-database connectivity** — PostgreSQL (primary), Redis (cache/broker), SQL Server (optional), pgvector (vector store)


## Demo & Core Views

Run the stack locally, then open the dashboard and upload a sample file:
```bash
docker compose up --build
# then visit http://localhost:3000 and upload a PDF from /test-documents
```

The application provides three primary interactive views:
- **Dashboard** (`/dashboard`): Central document management view showing document status, risk ratings, and quick actions.
- **Document View** (`/documents/[id]`): Split-pane review interface with native extracted text, clickable clause risk highlights, and confidence badges.
- **Report View** (`/reports/[id]`): Clean, printable memorandum layout featuring plain-English summaries, clause risk breakdown, and audit tracking.

## Quick Start (Install & Run)

**Prerequisites:** Node.js 20+, Python 3.11+, Git. Docker optional but recommended.

### Unix / macOS
```bash
git clone https://github.com/Kushagra901/Legal-analyzer.git
cd Legal-analyzer/backend
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
git clone https://github.com/Kushagra901/Legal-analyzer.git
cd Legal-analyzer\backend
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
Start-Process uvicorn app.main:app --reload --port 8000

cd ..\frontend
npm install
copy .env.example .env.local
npm run dev
```

### One-Command Local Launch (Windows PowerShell)

Once the initial setup is complete, you can start the entire local stack with one command from the project root:

```powershell
.\start-all.ps1
```

This script:
1. **Checks Ollama:** Verifies `http://localhost:11434` is active, or launches `ollama serve` in a new window if it isn't running.
2. **Starts Backend:** Opens a new window, activates `backend\.venv`, and starts FastAPI (`uvicorn app.main:app --reload` on `http://localhost:8000`).
3. **Starts Frontend:** Opens a new window and starts Next.js (`npm run dev` on `http://localhost:3000`).
4. **Health Check Summary:** Waits a few seconds for services to initialize, tests each health endpoint, and prints a status table.

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
/frontend
  /app                  → routes: (auth), (dashboard)/{dashboard,documents/[id],reports/[id],admin,review}
  /components           → ui/ (primitives), documents/, reports/
  /lib                  → api/, hooks/, supabase/

/backend
  /app
    /api/v1/routers     → auth, documents, reports, admin, system, analytics
    /services
      llm_service.py           → 3-tier LLM fallback: Claude → Gemini → Rule-based
      ocr_service.py           → PDF/DOCX text extraction + Tesseract OCR fallback
      risk_service.py          → Safety score calculation and risk level classification
      compliance_service.py    → Rule-set compliance auditing (NDA, GDPR, Employment, etc.)
      embedding_service.py     → 768-dim vector embeddings + pgvector semantic search
      chat_service.py          → RAG-powered document Q&A with citation grounding
      spark_analytics_service.py    → PySpark batch analytics (risk distribution, trends)
      event_streaming_service.py    → Apache Kafka producer/consumer for document events
      lakehouse_service.py          → Medallion architecture (Bronze → Silver → Gold)
      analytics_etl_service.py      → Star schema ETL: OLTP → dimensional fact tables
      data_quality_service.py       → Automated data validation and governance checks
      mcp_server.py                 → MCP protocol server for LLM tool access
      report_generator_service.py   → PDF/DOCX report generation via ReportLab
      storage_service.py            → Supabase Storage file operations
    /models             → SQLAlchemy ORM models + Pydantic v2 schemas
    /workers            → Celery async tasks (document analysis pipeline)
    /core               → config, database, auth, security, logging, rate limiting
  /migrations
    0001–0007           → Core OLTP schema (users, documents, clauses, etc.)
    0008                → Analytics star schema (dim_*, fact_*, SCD Type 2)
    0009                → SQL window function views (trends, distributions, cumulative)
  /databricks
    document_analysis_notebook.py  → Databricks notebook: Delta Lake medallion pipeline
    unity_catalog_config.py        → Unity Catalog 3-level namespace configuration
  /orchestration
    adf_pipeline.json              → Azure Data Factory pipeline definition
    airflow_dag.py                 → Apache Airflow DAG (TaskFlow API)
  /tests                → 18+ test modules covering all services

/docker-compose.yml     → Backend + n8n + Redis + Celery + Kafka + Zookeeper
/.github/workflows      → CI pipeline: lint, audit, test, build
```

### Data Flow

```
Upload → OCR/Extract → [Kafka: document.uploaded]
  → LLM Analyze (Claude/Gemini/Ollama) → Risk Score → Compliance Check
    → [Kafka: document.analyzed]
      → Chunk & Embed (768-dim pgvector) → ETL to Star Schema
        → [Kafka: document.completed]
          → Report Generate → Notify User
```

### ETL / Data Modelling Layer

The analytics layer implements a **star schema** dimensional model:
- **Dimensions:** `dim_document_types`, `dim_clause_categories`, `dim_risk_levels`, `dim_dates`
- **Facts:** `fact_document_analyses`, `fact_clause_risks`
- **SCD Type 2:** `dim_documents_scd2` tracks document re-analysis history with `effective_from`, `effective_to`, `is_current` columns and a PostgreSQL trigger

### Lakehouse Architecture (Medallion Pattern)

| Layer | Content | Storage |
|---|---|---|
| Bronze | Raw extracted text, OCR output | Append-only, immutable |
| Silver | Parsed clauses, risk flags, compliance results | Cleaned, validated |
| Gold | Aggregated analytics, risk reports | Business-ready |



## Data Model / Schema

### OLTP Layer (Operational)

| Entity | Key Fields |
|---|---|
| `users` | id, org_id, email, role |
| `organizations` | id, name, plan |
| `documents` | id, user_id, filename, status, safety_score, risk_level |
| `extracted_text` | id, document_id, content, method, parsing_confidence |
| `clauses` | id, document_id, clause_type, clause_text, confidence_score, category |
| `risk_flags` | id, clause_id, severity, explanation |
| `compliance_checks` | id, document_id, rule_set, result |
| `document_chunks` | id, document_id, chunk_text, chunk_index, embedding (vector 768) |
| `chat_messages` | id, document_id, user_id, role, content, citations, confidence |
| `deep_extractions` | id, document_id, deal_terms, obligations, risk_flags, redline_suggestions |
| `reports` | id, document_id, format, file_url |
| `audit_logs` | id, document_id, action, created_at |
| `clause_reviews` | id, clause_id, document_id, user_id, decision, note |
| `automation_runs` | id, document_id, workflow_name, status, retry_count |

### Analytics Layer (Star Schema)

| Entity | Type | Key Fields |
|---|---|---|
| `dim_document_types` | Dimension | id, type_name, description |
| `dim_clause_categories` | Dimension | id, category_name, description |
| `dim_risk_levels` | Dimension | id, level_name, severity_order, color_code |
| `dim_dates` | Dimension | date_key, year, quarter, month, day, is_weekend |
| `fact_document_analyses` | Fact | document_id, risk_level_id, safety_score, clause_count, high/med/low counts |
| `fact_clause_risks` | Fact | clause_id, category_id, risk_level_id, confidence_score |
| `dim_documents_scd2` | SCD Type 2 | document_id, safety_score, risk_level, effective_from, effective_to, is_current |

### Analytics Views (Window Functions)

| View | Window Functions Used |
|---|---|
| `v_document_risk_trends` | ROW_NUMBER, AVG (rolling 3), LAG, RANK |
| `v_clause_category_distribution` | COUNT (partition), DENSE_RANK, percentage calc |
| `v_user_activity_metrics` | SUM, FIRST_VALUE, NTILE quartiles |
| `v_compliance_violation_cumulative` | SUM (unbounded preceding), PERCENT_RANK |

Full schema: [`backend/migrations/`](./backend/migrations/).

### Database Migrations (Alembic)

Database schema evolutions are version-controlled using **Alembic**:

```bash
# Navigate to backend directory
cd backend

# Run all pending migrations to bring the database up to date
alembic upgrade head

# Check current migration revision
alembic current

# Roll back the most recent migration
alembic downgrade -1

# Generate a new auto-detected migration revision after modifying models
alembic revision --autogenerate -m "describe_schema_changes"
```

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

## Technology Stack

| Category | Technology | Role in Legal Analyzer |
|---|---|---|
| **Languages** | Python 3.11+, TypeScript 5, SQL | Backend services, frontend UI, analytics queries |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy | REST API, schema validation, ORM |
| **Frontend** | Next.js (App Router), Tailwind CSS, shadcn/ui | Dashboard, document viewer, report UI |
| **Database** | PostgreSQL (Supabase), pgvector | Primary OLTP store + 768-dim vector embeddings |
| **Big Data** | Apache Spark / PySpark | Batch analytics: risk distributions, clause trends |
| **Lakehouse** | Databricks, Delta Lake, Unity Catalog | Medallion architecture (Bronze → Silver → Gold) |
| **Streaming** | Apache Kafka, confluent-kafka | Document lifecycle event streaming |
| **Orchestration** | Azure Data Factory, Apache Airflow, n8n, Celery | Pipeline orchestration (multiple options) |
| **Data Modelling** | Star schema, SCD Type 2, dimensional modelling | Analytics layer: facts, dimensions, slowly changing dims |
| **AI/ML** | Claude API, Gemini API, Ollama, RAG, pgvector | Clause extraction, risk scoring, document Q&A |
| **MCP** | Model Context Protocol (JSON-RPC) | Exposing document data as LLM-queryable tools |
| **Cloud** | AWS (Supabase on AWS), Azure (ADF, DevOps), Vercel, Render | Deployment and infrastructure |
| **Databases** | PostgreSQL, Redis, SQL Server (optional), MongoDB (awareness) | Multi-database connectivity |
| **CI/CD** | GitHub Actions, Docker, docker-compose | Automated lint, audit, test, build pipeline |
| **Monitoring** | Sentry (error tracking) | Production observability |
| **Security** | Supabase Auth, RBAC, rate limiting, CORS, CSP headers | Authentication and access control |
| **Data Quality** | Custom governance service | Automated validation of extraction, embeddings, scores |
| **Version Control** | Git (branching: main, feature/**) | Source control with branch-based CI triggers |
| **OS** | Linux (Docker, CI runs ubuntu-latest) | Production runtime environment |

## Deployment

*Assumption: this project targets Vercel + Render (both free-tier friendly) rather than Heroku/GCP/AWS, matching the stack already chosen in `legal-analyzer-architecture.md`.*

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

**Before committing any screenshot, GIF, or demo video, check for:**
- [ ] Only fake/sample documents visible (e.g., "Acme Corp NDA — Jane Doe"), never a real user's real contract
- [ ] No real API key, token, or `.env` contents visible in any terminal, editor, or network-tab shot
- [ ] No real Supabase project URL/anon key visible in a settings or dashboard screenshot
- [ ] No real personal emails, phone numbers, or company names anywhere in frame
- [ ] Browser chrome (bookmarks bar, profile name) cropped out
- [ ] For videos/GIFs: scrub through every frame once at full resolution before committing — one visible frame is enough to leak a key

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

**Primary maintainer:** Kushagra ([@Kushagra901](https://github.com/Kushagra901)). For issues, feature requests, or inquiries, please open a [GitHub Issue](https://github.com/Kushagra901/Legal-analyzer/issues).

## License

**MIT License** — chosen because it's the most permissive common option for a learning/portfolio project, allowing others to freely use and build on the code with minimal friction, while you retain attribution.

## Acknowledgements & Credits

Built with [Next.js](https://nextjs.org), [FastAPI](https://fastapi.tiangolo.com), [SQLAlchemy](https://www.sqlalchemy.org), [Tailwind CSS](https://tailwindcss.com), [shadcn/ui](https://ui.shadcn.com), [pypdf](https://pypdf.readthedocs.io), the [Gemini API](https://ai.google.dev), and the [Claude API](https://docs.anthropic.com). Automation designed around [n8n](https://n8n.io). Analytics powered by [Apache Spark](https://spark.apache.org) and [PySpark](https://spark.apache.org/docs/latest/api/python/). Event streaming via [Apache Kafka](https://kafka.apache.org). Lakehouse architecture with [Databricks](https://databricks.com) and [Delta Lake](https://delta.io). Orchestration with [Azure Data Factory](https://azure.microsoft.com/en-us/products/data-factory) and [Apache Airflow](https://airflow.apache.org).

## Appendix

- Architecture & schema: [`legal-analyzer-architecture.md`](./legal-analyzer-architecture.md)
- AI agent conventions: [`AGENTS.md`](./AGENTS.md)

**Command summary:**
```bash
uvicorn app.main:app --reload --port 8000   # backend
npm run dev                                  # frontend
ruff check . && pytest                       # backend tests
npm run lint && npm test                     # frontend tests
docker compose up --build                    # full local stack
```

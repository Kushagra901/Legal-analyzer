"""Generate professional downloadable PDF report for MED-01 through MED-05 bug fixes."""

from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_pdf_report(output_path: Path) -> None:
    """Build a publication-grade PDF report compliant with AGENTS.md design tokens."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    # Palette
    c_navy = colors.HexColor("#0f2942")
    c_ink = colors.HexColor("#111827")
    c_muted = colors.HexColor("#4b5563")
    c_border = colors.HexColor("#d1d5db")
    c_bg_light = colors.HexColor("#f8fafc")
    c_green_bg = colors.HexColor("#ecfdf5")
    c_green_text = colors.HexColor("#065f46")
    c_code_bg = colors.HexColor("#f1f5f9")

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_navy,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_muted,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=c_navy,
        spaceBefore=14,
        spaceAfter=8,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=c_navy,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=c_ink,
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=c_ink,
    )

    badge_style = ParagraphStyle(
        "Badge_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=c_green_text,
        alignment=1,
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("Engineering Resolution Report: MED-01 through MED-05", title_style))
    elements.append(Paragraph(
        f"Legal Analyzer Platform &bull; Date: {datetime.now(UTC).strftime('%B %d, %Y')} &bull; Status: All 5 Issues Resolved & Verified",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=c_navy, spaceAfter=14))

    # Executive Summary Table
    elements.append(Paragraph("1. Executive Summary Matrix", h1_style))

    summary_data = [
        [
            Paragraph("<b>Issue ID</b>", body_style),
            Paragraph("<b>Architecture Label</b>", body_style),
            Paragraph("<b>Domain</b>", body_style),
            Paragraph("<b>Target File / Component</b>", body_style),
            Paragraph("<b>Status</b>", body_style),
        ],
        [
            Paragraph("<b>MED-01</b>", body_style),
            Paragraph("<code>DATA-DB-003-CONNECTION-POOLING</code>", body_style),
            Paragraph("Database Infrastructure", body_style),
            Paragraph("<code>backend/app/core/database.py</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>MED-02</b>", body_style),
            Paragraph("<code>OBS-LOG-001-STRUCTURED-LOGGING</code>", body_style),
            Paragraph("Observability & Logging", body_style),
            Paragraph("<code>backend/app/core/logging.py</code>, <code>main.py</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>MED-03</b>", body_style),
            Paragraph("<code>API-REST-001-PAGINATION</code>", body_style),
            Paragraph("API Scalability", body_style),
            Paragraph("<code>crud.py</code>, <code>admin.py</code>, <code>client.ts</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>MED-04</b>", body_style),
            Paragraph("<code>PERF-DB-001-RELATIONSHIP-EAGER-LOAD</code>", body_style),
            Paragraph("Database Performance", body_style),
            Paragraph("<code>database_models.py</code>, <code>crud.py</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>MED-05</b>", body_style),
            Paragraph("<code>DATA-DB-004-INDEX-OPTIMIZATION</code>", body_style),
            Paragraph("Database Performance", body_style),
            Paragraph("<code>database_models.py</code> (14 Indexes)", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
    ]

    t_summary = Table(summary_data, colWidths=[55, 160, 110, 140, 65])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (4, 1), (4, -1), c_green_bg),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 14))

    # Bug Details Section
    elements.append(Paragraph("2. Technical Problem, Resolution & Verification Details", h1_style))

    bugs = [
        {
            "id": "MED-01: Production Connection Pooling on SQLAlchemy Engine",
            "label": "DATA-DB-003-CONNECTION-POOLING",
            "files": "backend/app/core/database.py, backend/tests/test_database_pooling.py",
            "problem": "The database engine was created without explicit pool configuration, defaulting to 5 connections with no recycle timeout. Under concurrent traffic, PostgreSQL dropped idle connections, exhausting pool limits.",
            "solution": "Added driver-aware pooling in database.py with pool_size=10 (Postgres) / 5 (SQLite), max_overflow=20 / 10, pool_pre_ping=True (proactive ping for dead sockets), and pool_recycle=1800 (30-minute recycle window).",
            "code": "is_sqlite = settings.DATABASE_URL.startswith('sqlite')\nengine = create_engine(\n    settings.DATABASE_URL,\n    connect_args={'check_same_thread': False} if is_sqlite else {},\n    pool_size=10 if not is_sqlite else 5,\n    max_overflow=20 if not is_sqlite else 10,\n    pool_pre_ping=True,\n    pool_recycle=1800,\n)",
            "verification": "4 tests passed in tests/test_database_pooling.py verifying pool parameters and liveness pre-ping.",
        },
        {
            "id": "MED-02: Application Structured Logging & Print Elimination",
            "label": "OBS-LOG-001-STRUCTURED-LOGGING",
            "files": "backend/app/main.py, backend/app/core/logging.py, tasks.py, storage_service.py, ocr_service.py",
            "problem": "setup_logging() was never called in main.py, and the backend codebase relied on unformatted print() statements, preventing structured log ingestion in production and Sentry breadcrumbs.",
            "solution": "Implemented JSONLogFormatter in logging.py for production, called setup_logging() prior to FastAPI initialization in main.py, and converted all print() statements to structured logger calls. Enforced legal confidentiality: logged only document_id references, never raw text.",
            "code": "class JSONLogFormatter(logging.Formatter):\n    def format(self, record: logging.LogRecord) -> str:\n        return json.dumps({\n            'timestamp': datetime.now(timezone.utc).isoformat(),\n            'level': record.levelname,\n            'name': record.name,\n            'message': record.getMessage(),\n            'module': record.module,\n            'line': record.lineno,\n        })",
            "verification": "5 tests passed in tests/test_logging.py, including an AST scanner asserting 0 raw print() calls in backend/app/.",
        },
        {
            "id": "MED-03: Limit/Offset Pagination on List Endpoints",
            "label": "API-REST-001-PAGINATION",
            "files": "backend/app/models/schemas.py, crud.py, admin.py, frontend/lib/api/client.ts, dashboard/page.tsx",
            "problem": "GET /api/v1/documents and GET /api/v1/admin/audit-logs returned unbounded record arrays, causing query timeouts and browser payload bloat as document count grew.",
            "solution": "Created PaginatedDocumentList and PaginatedAuditLogList schemas (items, total, limit, offset). Added validated query parameters (limit le 100, default 50; offset ge 0, default 0). Updated TypeScript client and frontend dashboards to consume paginated items.",
            "code": "@router.get('', response_model=PaginatedDocumentList)\ndef list_documents(\n    limit: int = Query(default=50, ge=1, le=100),\n    offset: int = Query(default=0, ge=0),\n    current_user: User = Depends(get_current_user),\n    db: Session = Depends(get_db),\n) -> PaginatedDocumentList:\n    ...",
            "verification": "6 tests passed in tests/test_pagination.py; frontend TypeScript check npx tsc --noEmit passed with 0 errors.",
        },
        {
            "id": "MED-04: Elimination of N+1 Query Anti-Pattern in get_document",
            "label": "PERF-DB-001-RELATIONSHIP-EAGER-LOAD",
            "files": "backend/app/models/database_models.py, crud.py, backend/tests/test_eager_loading.py",
            "problem": "In get_document, the router queried all clauses and then looped over each clause issuing individual SQL queries for RiskFlag. A 60-clause contract resulted in 61 sequential database round trips.",
            "solution": "Established bidirectional ORM relationships in database_models.py (Clause.risk_flags and RiskFlag.clause) with selectin lazy loading, and applied options(joinedload(Clause.risk_flags)) in get_document to read risk flags directly from memory.",
            "code": "# Eager loaded clause and risk flag query\nclauses_db = (\n    db.query(Clause)\n    .options(joinedload(Clause.risk_flags))\n    .filter(Clause.document_id == document_id)\n    .order_by(Clause.clause_number.asc())\n    .all()\n)",
            "verification": "3 tests passed in tests/test_eager_loading.py using SQL cursor execution listeners verifying 0 extra queries across 10 clauses.",
        },
        {
            "id": "MED-05: Database Indexes on Foreign Key and Filtering Columns",
            "label": "DATA-DB-004-INDEX-OPTIMIZATION",
            "files": "backend/app/models/database_models.py, alembic migration, backend/tests/test_model_indexes.py",
            "problem": "Key relational foreign keys and filter columns lacked B-tree indexes, forcing full sequential table scans when resolving child records (clauses, risk flags, chunks, chat messages).",
            "solution": "Added index=True across 14 relational columns in database_models.py and created autogenerated Alembic migration 791aa19f3d22_add_foreign_key_indexes.py.",
            "code": "# 14 Indexed Columns:\nDocument.user_id, Clause.document_id, RiskFlag.clause_id, ExtractedText.document_id,\nComplianceCheck.document_id, LegalReference.document_id, Report.document_id,\nAuditLog.document_id, AutomationRun.document_id, ClauseReview.document_id,\nClauseReview.clause_id, DocumentChunk.document_id, ChatMessage.document_id,\nChatMessage.conversation_id",
            "verification": "2 tests passed in tests/test_model_indexes.py verifying column index properties and metadata reflection.",
        },
    ]

    for bug in bugs:
        bug_elements = []
        bug_elements.append(Paragraph(f"<b>{bug['id']}</b>", h2_style))
        bug_elements.append(Paragraph(f"<b>Label:</b> <code>{bug['label']}</code> &bull; <b>Target:</b> {bug['files']}", body_style))
        bug_elements.append(Paragraph(f"<b>Problem:</b> {bug['problem']}", body_style))
        bug_elements.append(Paragraph(f"<b>Solution:</b> {bug['solution']}", body_style))

        # Code snippet box
        code_p = Paragraph(bug["code"].replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)
        code_table = Table([[code_p]], colWidths=[530])
        code_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_code_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        bug_elements.append(code_table)
        bug_elements.append(Spacer(1, 4))
        bug_elements.append(Paragraph(f"<b>Verification:</b> {bug['verification']}", body_style))
        bug_elements.append(Spacer(1, 8))
        elements.append(KeepTogether(bug_elements))

    # Overall Verification Summary Table
    elements.append(Paragraph("3. Quality & Test Execution Metrics", h1_style))
    test_metrics = [
        [
            Paragraph("<b>Verification Scope</b>", body_style),
            Paragraph("<b>Execution Command</b>", body_style),
            Paragraph("<b>Results</b>", body_style),
        ],
        [
            Paragraph("Engineered Test Suite (20 Tests)", body_style),
            Paragraph("<code>pytest tests/test_database_pooling.py ...</code>", body_style),
            Paragraph("<b>20 passed</b> (100% success)", badge_style),
        ],
        [
            Paragraph("Regression Test Suite (16 Tests)", body_style),
            Paragraph("<code>pytest tests/test_upload.py ...</code>", body_style),
            Paragraph("<b>16 passed</b> (100% success)", badge_style),
        ],
        [
            Paragraph("Python Code Linter", body_style),
            Paragraph("<code>ruff check app tests</code>", body_style),
            Paragraph("<b>0 errors</b> (Clean)", badge_style),
        ],
        [
            Paragraph("Frontend TypeScript Compiler", body_style),
            Paragraph("<code>npx tsc --noEmit</code>", body_style),
            Paragraph("<b>0 errors</b> (Clean)", badge_style),
        ],
    ]
    t_metrics = Table(test_metrics, colWidths=[180, 230, 120])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (2, 1), (2, -1), c_green_bg),
    ]))
    elements.append(t_metrics)

    doc.build(elements)


if __name__ == "__main__":
    out_file = Path("d:/legal/BUG_RESOLUTION_REPORT.pdf")
    build_pdf_report(out_file)
    print(f"Generated PDF successfully at {out_file} (Size: {out_file.stat().st_size} bytes)")

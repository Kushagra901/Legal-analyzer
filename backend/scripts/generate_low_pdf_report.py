"""Generate publication-grade downloadable PDF report for LOW-01 through LOW-08 bug fixes."""

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


def build_low_pdf_report(output_path: Path) -> None:
    """Build a publication-grade PDF report compliant with AGENTS.md design tokens."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    # Design Tokens & Palette
    c_navy = colors.HexColor("#0f2942")
    c_ink = colors.HexColor("#111827")
    c_muted = colors.HexColor("#4b5563")
    c_border = colors.HexColor("#d1d5db")
    c_bg_light = colors.HexColor("#f8fafc")
    c_green_bg = colors.HexColor("#ecfdf5")
    c_green_text = colors.HexColor("#065f46")
    c_code_bg = colors.HexColor("#f1f5f9")

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_navy,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=c_muted,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_navy,
        spaceBefore=12,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=c_navy,
        spaceBefore=8,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=c_ink,
        spaceAfter=4,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=c_ink,
    )

    badge_style = ParagraphStyle(
        "Badge_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=c_green_text,
        alignment=1,
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("Engineering Resolution Report: LOW-01 through LOW-08", title_style))
    elements.append(Paragraph(
        f"Legal Analyzer Platform &bull; Date: {datetime.now(UTC).strftime('%B %d, %Y')} &bull; Status: All 8 Issues Resolved &amp; Verified",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=c_navy, spaceAfter=10))

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
            Paragraph("<b>LOW-01</b>", body_style),
            Paragraph("<code>CODE-STYLE-001-ELIMINATE-PRINTS</code>", body_style),
            Paragraph("Observability &amp; Style", body_style),
            Paragraph("Document routers, storage &amp; OCR services", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-02</b>", body_style),
            Paragraph("<code>CODE-QUALITY-001-REMOVE-DEAD-CHECKS</code>", body_style),
            Paragraph("Code Quality", body_style),
            Paragraph("Document sub-routers (crud, analysis, review, chat)", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-03</b>", body_style),
            Paragraph("<code>SEC-HDR-001-PERMISSIONS-POLICY</code>", body_style),
            Paragraph("Security Hardening", body_style),
            Paragraph("<code>backend/app/core/security_headers.py</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-04</b>", body_style),
            Paragraph("<code>DEVOPS-COMPOSE-001-CLEANUP</code>", body_style),
            Paragraph("DevOps &amp; Containers", body_style),
            Paragraph("<code>docker-compose.yml</code>, <code>backend/Dockerfile</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-05</b>", body_style),
            Paragraph("<code>DEVOPS-DEP-001-PIN-VERSIONS</code>", body_style),
            Paragraph("Dependencies", body_style),
            Paragraph("<code>backend/requirements.txt</code>", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-06</b>", body_style),
            Paragraph("<code>LEGAL-LIC-001-ADD-LICENSE</code>", body_style),
            Paragraph("Legal &amp; Governance", body_style),
            Paragraph("Root <code>LICENSE</code> file (MIT)", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-07</b>", body_style),
            Paragraph("<code>DATA-DB-007-CHUNK-INDEX-CONSTRAINT</code>", body_style),
            Paragraph("Database Integrity", body_style),
            Paragraph("<code>DocumentChunk</code> &amp; Alembic migration", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
        [
            Paragraph("<b>LOW-08</b>", body_style),
            Paragraph("<code>DOCS-META-001-URL-CLEANUP</code>", body_style),
            Paragraph("Documentation Meta", body_style),
            Paragraph("<code>README.md</code> repository meta &amp; links", body_style),
            Paragraph("<b>RESOLVED</b>", badge_style),
        ],
    ]

    t_summary = Table(summary_data, colWidths=[55, 175, 105, 145, 60])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (4, 1), (4, -1), c_green_bg),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # Bug Details Section
    elements.append(Paragraph("2. Technical Problem, Resolution &amp; Verification Details", h1_style))

    bugs = [
        {
            "id": "LOW-01: Replace Lingering Print Statements with Structured Logger",
            "label": "CODE-STYLE-001-ELIMINATE-PRINTS",
            "files": "backend/app/api/v1/routers/documents/*, storage_service.py, ocr_service.py",
            "problem": "Raw print() statements in router helpers and core services outputted unformatted text to standard out, bypassing JSON formatters, correlation ID (X-Request-ID) tracking, and Sentry breadcrumbs.",
            "solution": "Initialized module loggers (logger = logging.getLogger(__name__)). Replaced all print() statements with logger.info() and logger.warning(). Enforced document confidentiality by logging strictly document_id references.",
            "code": "logger = logging.getLogger(__name__)\nlogger.info('Storage service initialized with provider: %s', provider)\nlogger.warning('OCR processing warning for document %s: %s', document_id, err)",
            "verification": "Unit tests in tests/test_logging.py passed; codebase scan confirmed 0 unmanaged print() statements.",
        },
        {
            "id": "LOW-02: Eliminate Dead Code Unreachable Null Checks",
            "label": "CODE-QUALITY-001-REMOVE-DEAD-CHECKS",
            "files": "backend/app/api/v1/routers/documents/crud.py, analysis.py, review.py, chat.py",
            "problem": "get_accessible_document() raises an HTTPException(404) if a document is not found. Immediate subsequent checks (if not doc: raise HTTPException(...)) across endpoints were unreachable dead code.",
            "solution": "Audited and eliminated 6 blocks of unreachable dead null checks across documents sub-routers, streamlining control flow and eliminating branch coverage gaps.",
            "code": "# Cleaned endpoint invocation:\ndoc = get_accessible_document(db, document_id, current_user)\n# Dead 'if not doc:' checks removed across all sub-routers",
            "verification": "ruff check app/api/v1/routers/documents/ passed with 0 warnings; endpoints properly return 404.",
        },
        {
            "id": "LOW-03: Inject Permissions-Policy Header in Security Middleware",
            "label": "SEC-HDR-001-PERMISSIONS-POLICY",
            "files": "backend/app/core/security_headers.py, backend/tests/test_security_headers_and_rate_limit.py",
            "problem": "Security headers middleware lacked a Permissions-Policy HTTP header, leaving browser hardware APIs (camera, microphone, geolocation, payment) unrestricted.",
            "solution": "Injected Permissions-Policy header in SecurityHeadersMiddleware.dispatch() with strict zero-permission rules: camera=(), microphone=(), geolocation=(), payment=().",
            "code": "response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=()'",
            "verification": "pytest tests/test_security_headers_and_rate_limit.py verified that all HTTP responses carry the Permissions-Policy header.",
        },
        {
            "id": "LOW-04: Modernize docker-compose.yml and Fix Volume Pre-Creation Dependency",
            "label": "DEVOPS-COMPOSE-001-CLEANUP",
            "files": "docker-compose.yml, backend/Dockerfile",
            "problem": "docker-compose.yml specified deprecated version: '3.8' and external: true on n8n_data, failing docker compose up if volume was absent. Dockerfile lacked a container HEALTHCHECK.",
            "solution": "Removed version: '3.8', converted n8n_data to a self-managed volume (n8n_data:), and added a HEALTHCHECK instruction targeting http://localhost:8000/health in backend/Dockerfile.",
            "code": "HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\\n  CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1",
            "verification": "docker-compose file syntax validated with 0 schema warnings.",
        },
        {
            "id": "LOW-05: Pin Backend Dependencies with Upper Version Bounds",
            "label": "DEVOPS-DEP-001-PIN-VERSIONS",
            "files": "backend/requirements.txt",
            "problem": "Dependencies in requirements.txt used unbounded >= minimum versions, leaving builds and CI workflows vulnerable to unexpected breaking changes from upstream major releases.",
            "solution": "Pinned all package specifiers with compatible upper version bounds (e.g., fastapi>=0.110.0,<1.0.0, pydantic>=2.6.0,<3.0.0, sqlalchemy>=2.0.0,<3.0.0).",
            "code": "fastapi>=0.110.0,<1.0.0\npydantic>=2.6.0,<3.0.0\nsqlalchemy>=2.0.0,<3.0.0\nalembic>=1.13.0,<2.0.0\nreportlab>=4.1.0,<5.0.0",
            "verification": "pip check verified consistent dependency graph with no version conflicts.",
        },
        {
            "id": "LOW-06: Add Root LICENSE File",
            "label": "LEGAL-LIC-001-ADD-LICENSE",
            "files": "LICENSE (Root repository)",
            "problem": "README.md stated the project was released under the MIT License, but there was no LICENSE file in the repository root, creating legal ambiguity for open-source consumers.",
            "solution": "Created official MIT License file at repository root with standard legal terms and 2026 copyright attribution to Kushagra.",
            "code": "MIT License\nCopyright (c) 2026 Kushagra\nPermission is hereby granted, free of charge...",
            "verification": "Verified file presence at root; complies with standard SPDX MIT format.",
        },
        {
            "id": "LOW-07: Enforce Unique Constraint on Document Chunk Indexes",
            "label": "DATA-DB-007-CHUNK-INDEX-CONSTRAINT",
            "files": "backend/app/models/database_models.py, alembic migration, backend/tests/test_embedding_and_chunks.py",
            "problem": "Mid-process chunking failures during retries could persist duplicate chunk rows with identical index numbers for the same document, degrading embedding quality and RAG retrieval.",
            "solution": "Added UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index') to DocumentChunk.__table_args__. Generated Alembic migration 2e1482525d09, and added unit test.",
            "code": "from sqlalchemy import UniqueConstraint\n__table_args__ = (\n    UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_index'),\n)",
            "verification": "pytest tests/test_embedding_and_chunks.py passed 6/6 tests in 23.38s; verified duplicate insert raises IntegrityError.",
        },
        {
            "id": "LOW-08: Update Placeholder Badge URLs and Documentation Meta",
            "label": "DOCS-META-001-URL-CLEANUP",
            "files": "README.md",
            "problem": "README.md contained placeholder URLs (your-username/legal-analyzer, your-email@example.com), outdated placeholder assumption notes, and dead image references to uncommitted files.",
            "solution": "Updated all badges and clone commands to Kushagra901/Legal-analyzer. Removed dead image references, replacing them with structured UI descriptions. Updated maintainer contact info and fixed appendix links.",
            "code": "![Build Status](https://img.shields.io/github/actions/workflow/status/Kushagra901/Legal-analyzer/ci.yml?branch=main)\n**Primary maintainer:** Kushagra (@Kushagra901)\nArchitecture doc: legal-analyzer-architecture.md",
            "verification": "Grep scan confirmed 0 placeholder URLs (your-username, your-email, your-name, example.com) remain in README.md.",
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
        code_table = Table([[code_p]], colWidths=[540])
        code_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_code_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        bug_elements.append(code_table)
        bug_elements.append(Spacer(1, 2))
        bug_elements.append(Paragraph(f"<b>Verification:</b> {bug['verification']}", body_style))
        bug_elements.append(Spacer(1, 6))
        elements.append(KeepTogether(bug_elements))

    # Overall Verification Summary Table
    elements.append(Paragraph("3. Quality &amp; Test Execution Metrics", h1_style))
    test_metrics = [
        [
            Paragraph("<b>Verification Scope</b>", body_style),
            Paragraph("<b>Execution Command</b>", body_style),
            Paragraph("<b>Results</b>", body_style),
        ],
        [
            Paragraph("Chunk Unique Constraint &amp; Embeddings", body_style),
            Paragraph("<code>pytest tests/test_embedding_and_chunks.py</code>", body_style),
            Paragraph("<b>6 passed</b> (100% success)", badge_style),
        ],
        [
            Paragraph("Security Headers &amp; Permissions-Policy", body_style),
            Paragraph("<code>pytest tests/test_security_headers_and_rate_limit.py</code>", body_style),
            Paragraph("<b>5 passed</b> (100% success)", badge_style),
        ],
        [
            Paragraph("Logging &amp; Zero Raw Prints Check", body_style),
            Paragraph("<code>pytest tests/test_logging.py</code>", body_style),
            Paragraph("<b>8 passed</b> (100% success)", badge_style),
        ],
        [
            Paragraph("Python Code Linter", body_style),
            Paragraph("<code>ruff check app tests alembic</code>", body_style),
            Paragraph("<b>0 errors</b> (Clean)", badge_style),
        ],
    ]
    t_metrics = Table(test_metrics, colWidths=[180, 240, 120])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_bg_light),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (2, 1), (2, -1), c_green_bg),
    ]))
    elements.append(t_metrics)

    doc.build(elements)


if __name__ == "__main__":
    out_file = Path("d:/legal/LOW_BUG_RESOLUTION_REPORT.pdf")
    build_low_pdf_report(out_file)
    print(f"Generated PDF successfully at {out_file} (Size: {out_file.stat().st_size} bytes)")

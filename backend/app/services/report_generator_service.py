"""
Report Generator Service.
Generates structured, publication-grade PDF and DOCX legal memorandum reports
rendering structured findings in strict sequential order:
1. Document Overview
2. Parties Involved
3. Key Dates
4. Important Clauses (grouped by category, showing severity, confidence score, and plain-English explanation)
5. Risk Flags
6. Missing or Unclear Sections
7. Plain-English Summary
8. Suggested Next Review Actions
"""
import io
from datetime import datetime
from typing import Any

import docx
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count
    along with running header and footer.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(40, 755, "LEGAL ANALYZER — AI REVIEW MEMORANDUM")
            self.drawRightString(572, 755, "CONFIDENTIAL & PRIVILEGED")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(40, 747, 572, 747)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)

        disclaimer_note = "Assists legal review — does not replace a licensed lawyer."
        self.drawString(40, 30, disclaimer_note)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 30, page_str)
        self.restoreState()


class ReportGeneratorService:
    """
    Service for generating structured legal audit memorandum reports in PDF and DOCX formats.
    """

    DISCLAIMER_TEXT = (
        "CONFIDENTIAL LEGAL REVIEW ASSISTANCE MEMORANDUM. This automated assessment is generated "
        "to assist legal review and triage. It does not constitute formal legal advice and never replaces "
        "the counsel of a licensed attorney. All confidence indicators and risk flags should be independently verified."
    )

    def __init__(self) -> None:
        self.navy = colors.HexColor("#0F172A")
        self.navy_light = colors.HexColor("#1E293B")
        self.slate_dark = colors.HexColor("#334155")
        self.slate_muted = colors.HexColor("#64748B")
        self.border_gray = colors.HexColor("#CBD5E1")
        self.bg_light = colors.HexColor("#F8FAFC")
        self.bg_warn = colors.HexColor("#FEF2F2")

        self.color_high = colors.HexColor("#DC2626")
        self.color_medium = colors.HexColor("#D97706")
        self.color_low = colors.HexColor("#16A34A")

    def _normalize_report_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize report data input structure with safe defaults.
        """
        normalized = {
            "document_id": str(data.get("document_id", "")),
            "filename": str(data.get("filename", "Untitled Document")),
            "generated_at": data.get("generated_at") or datetime.now().strftime("%B %d, %Y at %H:%M UTC"),
            "safety_score": data.get("safety_score") if data.get("safety_score") is not None else 100,
            "risk_level": str(data.get("risk_level", "LOW")).upper(),
            "document_overview": data.get("document_overview") or data.get("summary", "No document overview available."),
            "parties": data.get("parties") or [],
            "key_dates": data.get("key_dates") or {},
            "clauses": data.get("clauses") or [],
            "risk_flags": data.get("risk_flags") or [],
            "missing_sections": data.get("missing_sections") or [],
            "plain_english_summary": data.get("plain_english_summary") or data.get("summary", "No plain-English summary available."),
            "recommendations": data.get("recommendations") or [],
            "citations": data.get("citations") or [],
            "compliance_violations": data.get("compliance_violations") or []
        }

        # Normalize parties to string list
        if isinstance(normalized["parties"], dict):
            normalized["parties"] = [f"{k}: {v}" for k, v in normalized["parties"].items()]
        elif isinstance(normalized["parties"], list):
            clean_parties = []
            for p in normalized["parties"]:
                if isinstance(p, dict):
                    clean_parties.append(p.get("name") or p.get("party") or str(p))
                elif p:
                    clean_parties.append(str(p))
            normalized["parties"] = clean_parties

        # Extract risk flags if not explicitly provided
        if not normalized["risk_flags"]:
            for idx, c in enumerate(normalized["clauses"], 1):
                severity = str(c.get("severity") or c.get("risk_level") or "LOW").upper()
                explanation = c.get("explanation") or ""
                c_type = c.get("type") or c.get("clause_type") or f"Clause {idx}"
                if severity in ("MEDIUM", "HIGH") or explanation:
                    normalized["risk_flags"].append({
                        "clause_type": c_type,
                        "severity": severity,
                        "explanation": explanation or f"Elevated {severity} risk identified in {c_type}."
                    })

        # Add compliance violations to risk flags if present
        for v in normalized["compliance_violations"]:
            normalized["risk_flags"].append({
                "clause_type": "Compliance Policy Audit",
                "severity": "HIGH",
                "explanation": str(v)
            })

        return normalized

    # =========================================================================
    # PDF GENERATION (ReportLab)
    # =========================================================================

    def generate_pdf(self, raw_data: dict[str, Any]) -> bytes:
        """
        Generate a professional PDF memorandum report following the required 8-section layout.
        """
        data = self._normalize_report_data(raw_data)
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=45,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=self.navy,
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=self.slate_muted,
            spaceAfter=10
        )

        section_heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=self.navy,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        subsection_heading_style = ParagraphStyle(
            "SubsectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=self.navy_light,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=self.navy_light,
            spaceAfter=6
        )

        callout_style = ParagraphStyle(
            "CalloutText",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=self.slate_dark
        )

        finding_num_style = ParagraphStyle(
            "FindingNum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=self.navy
        )

        finding_text_style = ParagraphStyle(
            "FindingText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=self.navy_light
        )

        clause_quote_style = ParagraphStyle(
            "ClauseQuote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=self.slate_muted,
            leftIndent=10,
            spaceBefore=3,
            spaceAfter=4
        )

        story: list[Any] = []

        # ---------------------------------------------------------------------
        # Header Block
        # ---------------------------------------------------------------------
        story.append(Paragraph("LEGAL REVIEW MEMORANDUM", title_style))
        meta_sub = (
            f"<b>Document:</b> {data['filename']} &nbsp;|&nbsp; "
            f"<b>Date:</b> {data['generated_at']} &nbsp;|&nbsp; "
            f"<b>ID:</b> {data['document_id'][:12]}"
        )
        story.append(Paragraph(meta_sub, subtitle_style))

        # Metadata & Score Banner Table
        score_val = data["safety_score"]
        risk_val = data["risk_level"]
        risk_color = self.color_high if risk_val == "HIGH" else (self.color_medium if risk_val == "MEDIUM" else self.color_low)

        summary_table_data = [
            [
                Paragraph(f"<b>Overall Safety Score</b><br/><font size='16' color='{self.navy.hexval()}'><b>{score_val}</b></font><font size='9' color='#64748B'> / 100</font>", body_style),
                Paragraph(f"<b>Risk Assessment Level</b><br/><font size='14' color='{risk_color.hexval()}'><b>{risk_val} RISK</b></font>", body_style),
                Paragraph(f"<b>Clauses Reviewed:</b> {len(data['clauses'])}<br/><b>Risk Flags:</b> {len(data['risk_flags'])}", body_style)
            ]
        ]
        summary_table = Table(summary_table_data, colWidths=[175, 175, 182])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.bg_light),
            ("BOX", (0, 0), (-1, -1), 0.75, self.border_gray),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_gray),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 8))

        # Disclaimer Box
        disclaimer_table = Table([[Paragraph(self.DISCLAIMER_TEXT, callout_style)]], colWidths=[532])
        disclaimer_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, self.border_gray),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(disclaimer_table)
        story.append(Spacer(1, 10))

        # ---------------------------------------------------------------------
        # 1. Document Overview
        # ---------------------------------------------------------------------
        story.append(Paragraph("1.0 Document Overview", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))
        story.append(Paragraph(data["document_overview"], body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 2. Parties Involved
        # ---------------------------------------------------------------------
        story.append(Paragraph("2.0 Parties Involved", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        if data["parties"]:
            parties_table_data = [
                [Paragraph("<b>#</b>", finding_num_style), Paragraph("<b>Party / Entity Name</b>", finding_num_style), Paragraph("<b>Designation / Role</b>", finding_num_style)]
            ]
            for idx, p in enumerate(data["parties"], 1):
                role = "First Party / Signatory" if idx == 1 else ("Second Party / Counterparty" if idx == 2 else "Participating Entity")
                parties_table_data.append([
                    Paragraph(f"2.{idx}", body_style),
                    Paragraph(f"<b>{p}</b>", body_style),
                    Paragraph(role, body_style)
                ])

            ptable = Table(parties_table_data, colWidths=[40, 320, 172])
            ptable.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.bg_light),
                ("BOX", (0, 0), (-1, -1), 0.5, self.border_gray),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_gray),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(ptable)
        else:
            story.append(Paragraph("2.1 No specific party entities identified in the agreement text.", body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 3. Key Dates
        # ---------------------------------------------------------------------
        story.append(Paragraph("3.0 Key Dates & Timeline", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        key_dates = data["key_dates"]
        if isinstance(key_dates, dict) and key_dates:
            dates_table_data = [
                [Paragraph("<b>#</b>", finding_num_style), Paragraph("<b>Contract Event / Term</b>", finding_num_style), Paragraph("<b>Designated Date / Provision</b>", finding_num_style)]
            ]
            for idx, (k, v) in enumerate(key_dates.items(), 1):
                clean_k = k.replace("_", " ").title()
                dates_table_data.append([
                    Paragraph(f"3.{idx}", body_style),
                    Paragraph(f"<b>{clean_k}</b>", body_style),
                    Paragraph(str(v), body_style)
                ])
            dtable = Table(dates_table_data, colWidths=[40, 240, 252])
            dtable.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.bg_light),
                ("BOX", (0, 0), (-1, -1), 0.5, self.border_gray),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, self.border_gray),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(dtable)
        elif isinstance(key_dates, list) and key_dates:
            for idx, d_item in enumerate(key_dates, 1):
                story.append(Paragraph(f"<b>3.{idx}</b> {d_item}", body_style))
        else:
            story.append(Paragraph("3.1 Key dates are not explicitly designated or are dependent on execution date.", body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 4. Important Clauses (Grouped by Category)
        # ---------------------------------------------------------------------
        story.append(Paragraph("4.0 Important Clauses (Grouped by Category)", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        # Group clauses by category
        grouped_clauses: dict[str, list[dict]] = {}
        for c in data["clauses"]:
            cat = c.get("category") or "General & Boilerplate"
            grouped_clauses.setdefault(cat, []).append(c)

        if not grouped_clauses:
            story.append(Paragraph("4.1 No specific standard clauses extracted from document text.", body_style))
        else:
            cat_idx = 1
            for cat_name, c_list in grouped_clauses.items():
                story.append(Paragraph(f"4.{cat_idx} Category: {cat_name}", subsection_heading_style))
                c_idx = 1
                for c in c_list:
                    c_type = c.get("type") or c.get("clause_type") or "Clause"
                    severity = str(c.get("severity") or c.get("risk_level") or "LOW").upper()
                    conf = c.get("confidence_score")
                    conf_str = f" | Confidence: {int(conf * 100)}%" if conf is not None else ""
                    explanation = c.get("explanation") or "Standard contractual provision."
                    text_snippet = c.get("text") or c.get("clause_text") or ""

                    sev_color = self.color_high.hexval() if severity == "HIGH" else (self.color_medium.hexval() if severity == "MEDIUM" else self.color_low.hexval())

                    clause_header = (
                        f"<b>Finding 4.{cat_idx}.{c_idx}: {c_type}</b> "
                        f"[<font color='{sev_color}'><b>{severity} SEVERITY</b></font>{conf_str}]"
                    )

                    clause_block = [
                        Paragraph(clause_header, finding_num_style),
                        Paragraph(f"<b>Assessment:</b> {explanation}", finding_text_style),
                    ]
                    if text_snippet:
                        truncated_quote = (text_snippet[:240] + "...") if len(text_snippet) > 240 else text_snippet
                        clause_block.append(Paragraph(f'<b>Excerpt:</b> "{truncated_quote}"', clause_quote_style))

                    clause_table = Table([[clause_block]], colWidths=[532])
                    clause_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), self.bg_light),
                        ("BOX", (0, 0), (-1, -1), 0.5, self.border_gray),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]))
                    story.append(KeepTogether([clause_table, Spacer(1, 4)]))
                    c_idx += 1
                cat_idx += 1

        story.append(Spacer(1, 4))

        # ---------------------------------------------------------------------
        # 5. Risk Flags
        # ---------------------------------------------------------------------
        story.append(Paragraph("5.0 Risk Flags & Warning Items", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        if data["risk_flags"]:
            for idx, rf in enumerate(data["risk_flags"], 1):
                sev = str(rf.get("severity", "MEDIUM")).upper()
                c_name = rf.get("clause_type") or "Risk Item"
                exp = rf.get("explanation") or ""
                sev_color = self.color_high.hexval() if sev == "HIGH" else (self.color_medium.hexval() if sev == "MEDIUM" else self.color_low.hexval())

                rf_header = f"<b>Risk 5.{idx}: {c_name}</b> — [<font color='{sev_color}'><b>{sev} PRIORITY</b></font>]"
                rf_content = [
                    Paragraph(rf_header, finding_num_style),
                    Paragraph(f"<b>Risk Analysis:</b> {exp}", finding_text_style)
                ]

                rf_table = Table([[rf_content]], colWidths=[532])
                rf_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), self.bg_warn if sev == "HIGH" else self.bg_light),
                    ("BOX", (0, 0), (-1, -1), 0.5, self.color_high if sev == "HIGH" else self.border_gray),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(KeepTogether([rf_table, Spacer(1, 4)]))
        else:
            story.append(Paragraph("5.1 No critical risk flags detected in the analyzed clauses.", body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 6. Missing or Unclear Sections
        # ---------------------------------------------------------------------
        story.append(Paragraph("6.0 Missing or Unclear Provisions", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        if data["missing_sections"]:
            for idx, sec in enumerate(data["missing_sections"], 1):
                story.append(Paragraph(
                    f"<b>6.{idx} Missing Protection: {sec}</b><br/>"
                    f"<font color='#64748B'>Customary contractual safeguard is absent. Consider inserting standard terms during redlining.</font>",
                    body_style
                ))
                story.append(Spacer(1, 2))
        else:
            story.append(Paragraph("6.1 All standard structural protections appear represented in the document.", body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 7. Plain-English Summary
        # ---------------------------------------------------------------------
        story.append(Paragraph("7.0 Plain-English Executive Summary", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))
        story.append(Paragraph(data["plain_english_summary"], body_style))
        story.append(Spacer(1, 6))

        # ---------------------------------------------------------------------
        # 8. Suggested Next Review Actions
        # ---------------------------------------------------------------------
        story.append(Paragraph("8.0 Suggested Next Review Actions", section_heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=self.border_gray, spaceBefore=1, spaceAfter=6))

        if data["recommendations"]:
            for idx, rec in enumerate(data["recommendations"], 1):
                story.append(Paragraph(f"<b>8.{idx} Action Item:</b> {rec}", body_style))
                story.append(Spacer(1, 2))
        else:
            story.append(Paragraph("8.1 Perform legal counsel review prior to formal execution.", body_style))
            story.append(Paragraph("8.2 Verify governing jurisdiction and indemnification limits.", body_style))

        # Build document with NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    # =========================================================================
    # DOCX GENERATION (python-docx)
    # =========================================================================

    def _set_cell_background(self, cell, hex_color: str):
        """Helper to set cell background color in docx."""
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        tc_pr.append(shd)

    def _set_cell_margins(self, cell, top=100, bottom=100, left=150, right=150):
        """Helper to set cell padding in docx."""
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_mar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
        tc_pr.append(tc_mar)

    def generate_docx(self, raw_data: dict[str, Any]) -> bytes:
        """
        Generate a professional DOCX memorandum report following the required 8-section layout.
        """
        data = self._normalize_report_data(raw_data)
        doc = docx.Document()

        # Set page margins (0.75 inch)
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        # Base Normal Style
        normal_style = doc.styles["Normal"]
        normal_style.font.name = "Calibri"
        normal_style.font.size = Pt(10)
        normal_style.font.color.rgb = RGBColor(15, 23, 42)

        # Title
        p_title = doc.add_paragraph()
        run_title = p_title.add_run("LEGAL REVIEW MEMORANDUM")
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(20)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(15, 23, 42)
        p_title.paragraph_format.space_after = Pt(2)

        # Subtitle
        p_sub = doc.add_paragraph()
        p_sub.add_run(f"Document: {data['filename']}  |  Date: {data['generated_at']}  |  ID: {data['document_id'][:12]}").font.color.rgb = RGBColor(100, 116, 139)
        p_sub.paragraph_format.space_after = Pt(12)

        # Summary Banner Table
        banner = doc.add_table(rows=1, cols=3)
        banner.alignment = WD_TABLE_ALIGNMENT.CENTER
        banner.autofit = False

        c0, c1, c2 = banner.rows[0].cells
        c0.width = Inches(2.3)
        c1.width = Inches(2.3)
        c2.width = Inches(2.4)

        for cell in (c0, c1, c2):
            self._set_cell_background(cell, "F8FAFC")
            self._set_cell_margins(cell, top=120, bottom=120, left=150, right=150)

        p0 = c0.paragraphs[0]
        p0.add_run("Overall Safety Score\n").font.bold = True
        run_sc = p0.add_run(f"{data['safety_score']}")
        run_sc.font.size = Pt(16)
        run_sc.font.bold = True
        p0.add_run(" / 100").font.color.rgb = RGBColor(100, 116, 139)

        p1 = c1.paragraphs[0]
        p1.add_run("Risk Level\n").font.bold = True
        run_rk = p1.add_run(f"{data['risk_level']} RISK")
        run_rk.font.size = Pt(14)
        run_rk.font.bold = True
        if data["risk_level"] == "HIGH":
            run_rk.font.color.rgb = RGBColor(220, 38, 38)
        elif data["risk_level"] == "MEDIUM":
            run_rk.font.color.rgb = RGBColor(217, 119, 6)
        else:
            run_rk.font.color.rgb = RGBColor(22, 163, 74)

        p2 = c2.paragraphs[0]
        p2.add_run("Review Stats\n").font.bold = True
        p2.add_run(f"Clauses: {len(data['clauses'])}  |  Risk Flags: {len(data['risk_flags'])}")

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Disclaimer Box
        disc_table = doc.add_table(rows=1, cols=1)
        disc_cell = disc_table.rows[0].cells[0]
        disc_cell.width = Inches(7.0)
        self._set_cell_background(disc_cell, "F1F5F9")
        self._set_cell_margins(disc_cell, top=100, bottom=100, left=150, right=150)
        p_disc = disc_cell.paragraphs[0]
        r_disc = p_disc.add_run(self.DISCLAIMER_TEXT)
        r_disc.font.italic = True
        r_disc.font.size = Pt(8.5)
        r_disc.font.color.rgb = RGBColor(71, 85, 105)

        doc.add_paragraph().paragraph_format.space_after = Pt(10)

        # ---------------------------------------------------------------------
        # 1. Document Overview
        # ---------------------------------------------------------------------
        h1 = doc.add_heading("1.0 Document Overview", level=1)
        h1.style.font.color.rgb = RGBColor(15, 23, 42)
        doc.add_paragraph(data["document_overview"])

        # ---------------------------------------------------------------------
        # 2. Parties Involved
        # ---------------------------------------------------------------------
        h2 = doc.add_heading("2.0 Parties Involved", level=1)
        h2.style.font.color.rgb = RGBColor(15, 23, 42)

        if data["parties"]:
            ptable = doc.add_table(rows=1, cols=3)
            ptable.alignment = WD_TABLE_ALIGNMENT.CENTER
            ptable.rows[0].cells[0].paragraphs[0].add_run("#").font.bold = True
            ptable.rows[0].cells[1].paragraphs[0].add_run("Party Name / Entity").font.bold = True
            ptable.rows[0].cells[2].paragraphs[0].add_run("Designation / Role").font.bold = True

            for idx, p in enumerate(data["parties"], 1):
                row = ptable.add_row()
                row.cells[0].paragraphs[0].add_run(f"2.{idx}")
                row.cells[1].paragraphs[0].add_run(str(p)).font.bold = True
                role = "First Party / Signatory" if idx == 1 else ("Second Party / Counterparty" if idx == 2 else "Participating Entity")
                row.cells[2].paragraphs[0].add_run(role)

            for row in ptable.rows:
                self._set_cell_margins(row.cells[0], 60, 60, 100, 100)
                self._set_cell_margins(row.cells[1], 60, 60, 100, 100)
                self._set_cell_margins(row.cells[2], 60, 60, 100, 100)
        else:
            doc.add_paragraph("2.1 No specific party entities identified in the agreement text.")

        # ---------------------------------------------------------------------
        # 3. Key Dates
        # ---------------------------------------------------------------------
        h3 = doc.add_heading("3.0 Key Dates & Timeline", level=1)
        h3.style.font.color.rgb = RGBColor(15, 23, 42)

        key_dates = data["key_dates"]
        if isinstance(key_dates, dict) and key_dates:
            dtable = doc.add_table(rows=1, cols=3)
            dtable.alignment = WD_TABLE_ALIGNMENT.CENTER
            dtable.rows[0].cells[0].paragraphs[0].add_run("#").font.bold = True
            dtable.rows[0].cells[1].paragraphs[0].add_run("Contract Event / Term").font.bold = True
            dtable.rows[0].cells[2].paragraphs[0].add_run("Designated Date / Provision").font.bold = True

            for idx, (k, v) in enumerate(key_dates.items(), 1):
                row = dtable.add_row()
                row.cells[0].paragraphs[0].add_run(f"3.{idx}")
                row.cells[1].paragraphs[0].add_run(k.replace("_", " ").title()).font.bold = True
                row.cells[2].paragraphs[0].add_run(str(v))

            for row in dtable.rows:
                self._set_cell_margins(row.cells[0], 60, 60, 100, 100)
                self._set_cell_margins(row.cells[1], 60, 60, 100, 100)
                self._set_cell_margins(row.cells[2], 60, 60, 100, 100)
        elif isinstance(key_dates, list) and key_dates:
            for idx, d_item in enumerate(key_dates, 1):
                doc.add_paragraph(f"3.{idx} {d_item}")
        else:
            doc.add_paragraph("3.1 Key dates are not explicitly designated or are dependent on execution date.")

        # ---------------------------------------------------------------------
        # 4. Important Clauses (Grouped by Category)
        # ---------------------------------------------------------------------
        h4 = doc.add_heading("4.0 Important Clauses (Grouped by Category)", level=1)
        h4.style.font.color.rgb = RGBColor(15, 23, 42)

        grouped_clauses: dict[str, list[dict]] = {}
        for c in data["clauses"]:
            cat = c.get("category") or "General & Boilerplate"
            grouped_clauses.setdefault(cat, []).append(c)

        if not grouped_clauses:
            doc.add_paragraph("4.1 No specific standard clauses extracted.")
        else:
            cat_idx = 1
            for cat_name, c_list in grouped_clauses.items():
                h_cat = doc.add_heading(f"4.{cat_idx} Category: {cat_name}", level=2)
                h_cat.style.font.color.rgb = RGBColor(30, 41, 59)
                c_idx = 1
                for c in c_list:
                    c_type = c.get("type") or c.get("clause_type") or "Clause"
                    severity = str(c.get("severity") or c.get("risk_level") or "LOW").upper()
                    conf = c.get("confidence_score")
                    conf_str = f" | Confidence: {int(conf * 100)}%" if conf is not None else ""
                    explanation = c.get("explanation") or "Standard contractual provision."
                    text_snippet = c.get("text") or c.get("clause_text") or ""

                    p_cl = doc.add_paragraph()
                    r_h = p_cl.add_run(f"Finding 4.{cat_idx}.{c_idx}: {c_type} ")
                    r_h.font.bold = True
                    r_sev = p_cl.add_run(f"[{severity} SEVERITY{conf_str}]\n")
                    r_sev.font.bold = True
                    if severity == "HIGH":
                        r_sev.font.color.rgb = RGBColor(220, 38, 38)
                    elif severity == "MEDIUM":
                        r_sev.font.color.rgb = RGBColor(217, 119, 6)
                    else:
                        r_sev.font.color.rgb = RGBColor(22, 163, 74)

                    p_cl.add_run(f"Assessment: {explanation}\n")
                    if text_snippet:
                        truncated = (text_snippet[:240] + "...") if len(text_snippet) > 240 else text_snippet
                        r_qt = p_cl.add_run(f'Excerpt: "{truncated}"')
                        r_qt.font.italic = True
                        r_qt.font.color.rgb = RGBColor(100, 116, 139)

                    p_cl.paragraph_format.space_after = Pt(8)
                    c_idx += 1
                cat_idx += 1

        # ---------------------------------------------------------------------
        # 5. Risk Flags
        # ---------------------------------------------------------------------
        h5 = doc.add_heading("5.0 Risk Flags & Warning Items", level=1)
        h5.style.font.color.rgb = RGBColor(15, 23, 42)

        if data["risk_flags"]:
            for idx, rf in enumerate(data["risk_flags"], 1):
                sev = str(rf.get("severity", "MEDIUM")).upper()
                c_name = rf.get("clause_type") or "Risk Item"
                exp = rf.get("explanation") or ""

                p_rf = doc.add_paragraph()
                r_rf = p_rf.add_run(f"Risk 5.{idx}: {c_name} — [{sev} PRIORITY]\n")
                r_rf.font.bold = True
                if sev == "HIGH":
                    r_rf.font.color.rgb = RGBColor(220, 38, 38)
                else:
                    r_rf.font.color.rgb = RGBColor(217, 119, 6)

                p_rf.add_run(f"Analysis: {exp}")
                p_rf.paragraph_format.space_after = Pt(6)
        else:
            doc.add_paragraph("5.1 No critical risk flags detected in the analyzed clauses.")

        # ---------------------------------------------------------------------
        # 6. Missing or Unclear Sections
        # ---------------------------------------------------------------------
        h6 = doc.add_heading("6.0 Missing or Unclear Provisions", level=1)
        h6.style.font.color.rgb = RGBColor(15, 23, 42)

        if data["missing_sections"]:
            for idx, sec in enumerate(data["missing_sections"], 1):
                p_ms = doc.add_paragraph()
                p_ms.add_run(f"6.{idx} Missing Protection: {sec}\n").font.bold = True
                p_ms.add_run("Customary contractual safeguard is absent. Consider inserting standard terms during redlining.").font.color.rgb = RGBColor(100, 116, 139)
                p_ms.paragraph_format.space_after = Pt(4)
        else:
            doc.add_paragraph("6.1 All standard structural protections appear represented in the document.")

        # ---------------------------------------------------------------------
        # 7. Plain-English Summary
        # ---------------------------------------------------------------------
        h7 = doc.add_heading("7.0 Plain-English Executive Summary", level=1)
        h7.style.font.color.rgb = RGBColor(15, 23, 42)
        doc.add_paragraph(data["plain_english_summary"])

        # ---------------------------------------------------------------------
        # 8. Suggested Next Review Actions
        # ---------------------------------------------------------------------
        h8 = doc.add_heading("8.0 Suggested Next Review Actions", level=1)
        h8.style.font.color.rgb = RGBColor(15, 23, 42)

        if data["recommendations"]:
            for idx, rec in enumerate(data["recommendations"], 1):
                p_rc = doc.add_paragraph()
                p_rc.add_run(f"8.{idx} Action Item: ").font.bold = True
                p_rc.add_run(str(rec))
                p_rc.paragraph_format.space_after = Pt(4)
        else:
            doc.add_paragraph("8.1 Perform legal counsel review prior to formal execution.")
            doc.add_paragraph("8.2 Verify governing jurisdiction and indemnification limits.")

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

"""
Reports router.
Handles retrieval and generation requests for legal memorandum reports.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_accessible_document, get_current_user
from app.core.database import get_db
from app.models import AuditLog, Clause, ComplianceCheck, LegalReference, RiskFlag, User
from app.models.schemas import CitationResponse, ClauseResponse, ReportResponse

router = APIRouter()

@router.get("/{document_id}", response_model=ReportResponse)
def get_report(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ReportResponse:
    """
    Retrieve generated memorandum audit report by document ID.
    """
    doc = get_accessible_document(db, document_id, current_user)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Load citations
    citations_db = db.query(LegalReference).filter(LegalReference.document_id == doc.id).all()
    citations = [
        CitationResponse(
            source=cit.source,
            citation=cit.citation
        )
        for cit in citations_db
    ]

    # Load clauses to build response and recommendations
    clauses_db = db.query(Clause).filter(Clause.document_id == doc.id).all()
    clauses = []
    recommendations = []

    for c_db in clauses_db:
        flags = db.query(RiskFlag).filter(RiskFlag.clause_id == c_db.id).all()
        severity = flags[0].severity if flags else "LOW"
        explanation = flags[0].explanation if flags else ""

        if severity in ("MEDIUM", "HIGH") and explanation:
            recommendations.append(f"Review the {c_db.clause_type} clause: {explanation}")

        clauses.append(
            ClauseResponse(
                id=str(c_db.id),
                type=c_db.clause_type,
                text=c_db.clause_text,
                risk_level=severity,
                severity=severity,
                explanation=explanation
            )
        )

    # Load compliance violations
    compliance_db = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc.id).first()
    if compliance_db:
        try:
            violations = json.loads(compliance_db.result)
            for v in violations:
                recommendations.append(v)
        except Exception:
            pass

    if not recommendations:
        recommendations.append("Confirm all provisions align with standard organizational templates and practices.")
        recommendations.append("Ensure the designated governing jurisdiction is acceptable for your operations before formal execution.")

    # Write audit log row for report viewed
    try:
        audit_log = AuditLog(
            document_id=doc.id,
            action=f"Report viewed: {doc.filename}"
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error writing report audit log: {e}")

    return ReportResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        report_url=f"/reports/{doc.id}.pdf",
        safety_score=doc.safety_score if doc.safety_score is not None else 100,
        risk_level=doc.risk_level if doc.risk_level is not None else "LOW",
        summary=doc.summary or "Analysis complete.",
        recommendations=recommendations,
        clauses=clauses,
        citations=citations
    )



"""
test_document_process_pipeline.py
Unit and integration tests for:
1. Consolidated master endpoint POST /api/v1/documents/{document_id}/process.
2. Sequential internal service execution:
   - ocr_service.extract_text(document_id)
   - llm_service.analyze_contract(document_id)
   - compliance_service.check_compliance(document_id)
   - report_generator_service.generate_report(document_id)
   - audit_service.log_event(document_id, "pipeline_completed")
3. Response contract: {"document_id": "...", "status": "completed"}.
4. Idempotency guarantees via the automation_runs ledger.
"""
import os
import sys
import uuid
from unittest.mock import patch

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    AutomationRun,
    Clause,
    ComplianceCheck,
    Document,
    ExtractedText,
    Organization,
    Report,
    RiskFlag,
    User,
)
from app.services.audit_service import AuditService
from app.services.compliance_service import ComplianceService
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.report_generator_service import ReportGeneratorService

# Setup in-memory SQLite database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user(request: Request, db: Session = Depends(override_get_db)):
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    org = db.query(Organization).filter(Organization.id == test_uuid).first()
    if not org:
        org = Organization(id=test_uuid, name="Test Org", plan="free")
        db.add(org)
        db.commit()
    user = db.query(User).filter(User.id == test_uuid).first()
    if not user:
        user = User(id=test_uuid, org_id=test_uuid, email="test@example.com", role="user")
        db.add(user)
        db.commit()
    return user


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Clear database tables and reset dependency overrides before each test."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    db = TestingSessionLocal()
    db.query(AuditLog).delete()
    db.query(AutomationRun).delete()
    db.query(RiskFlag).delete()
    db.query(Clause).delete()
    db.query(Report).delete()
    db.query(ComplianceCheck).delete()
    db.query(ExtractedText).delete()
    db.query(Document).delete()

    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    org = db.query(Organization).filter(Organization.id == test_uuid).first()
    if not org:
        org = Organization(id=test_uuid, name="Test Org", plan="free")
        db.add(org)
    user = db.query(User).filter(User.id == test_uuid).first()
    if not user:
        user = User(id=test_uuid, org_id=test_uuid, email="test@example.com", role="user")
        db.add(user)
    db.commit()
    db.close()
    yield
    app.dependency_overrides.clear()


# =============================================================================
# 1. Integration Tests for POST /api/v1/documents/{document_id}/process
# =============================================================================

def test_process_pipeline_runs_all_steps_and_updates_status_to_completed():
    """
    Verify master /process endpoint executes OCR, LLM analysis, compliance check,
    report generation, and audit logging, updating document status to 'completed'.
    """
    db = TestingSessionLocal()
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    sample_contract_text = (
        "CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT\n\n"
        "This Agreement is entered into by Disclosing Party and Receiving Party.\n"
        "1. Confidentiality Obligations: Receiving Party shall hold all Confidential Information in strict confidence.\n"
        "2. Limitation of Liability: In no event shall either party's aggregate liability exceed $10,000.\n"
        "3. Governing Law: This Agreement shall be governed by the laws of the State of Delaware."
    )

    doc = Document(
        id=doc_id,
        user_id=test_uuid,
        filename="test_nda_agreement.pdf",
        status="uploaded"
    )
    db.add(doc)

    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=sample_contract_text,
        method="native",
        parsing_confidence=1.0
    )
    db.add(extracted)
    db.commit()
    db.close()

    headers = {"X-Internal-Token": settings.INTERNAL_SERVICE_TOKEN or "test-internal-token"}
    response = client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Requirement 3: Return a single status object {"document_id": "...", "status": "completed"}
    assert data["document_id"] == str(doc_id)
    assert data["status"] == "completed"

    # Verify Document state in database
    db_verify = TestingSessionLocal()
    updated_doc = db_verify.query(Document).filter(Document.id == doc_id).first()
    assert updated_doc is not None
    assert updated_doc.status == "completed"
    assert updated_doc.error_message is None
    assert updated_doc.summary != ""
    assert updated_doc.safety_score is not None
    assert updated_doc.risk_level in ["LOW", "MEDIUM", "HIGH"]

    # Verify extracted clauses & risk flags
    clauses = db_verify.query(Clause).filter(Clause.document_id == doc_id).all()
    assert len(clauses) >= 1

    # Verify compliance check record
    compliance = db_verify.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc_id).first()
    assert compliance is not None
    assert compliance.rule_set is not None

    # Verify generated report
    report = db_verify.query(Report).filter(Report.document_id == doc_id).first()
    assert report is not None
    assert report.format == "pdf"
    assert report.file_url != ""

    # Verify audit log entry
    audit = db_verify.query(AuditLog).filter(
        AuditLog.document_id == doc_id,
        AuditLog.action.contains("pipeline_completed")
    ).first()
    assert audit is not None

    # Requirement 5: Verify automation_runs table
    auto_run = db_verify.query(AutomationRun).filter(
        AutomationRun.document_id == doc_id,
        AutomationRun.workflow_name == "Legal Analyzer Pipeline"
    ).first()
    assert auto_run is not None
    assert auto_run.status == "completed"
    db_verify.close()


def test_process_pipeline_idempotency_returns_completed_if_already_completed():
    """
    Verify idempotency: If automation_runs is already 'completed', /process returns
    completed status immediately without duplicate execution.
    """
    db = TestingSessionLocal()
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=test_uuid,
        filename="already_completed.pdf",
        status="completed"
    )
    db.add(doc)

    auto_run = AutomationRun(
        id=uuid.uuid4(),
        document_id=doc_id,
        workflow_name="Legal Analyzer Pipeline",
        status="completed",
        retry_count=0
    )
    db.add(auto_run)
    db.commit()
    db.close()

    headers = {"X-Internal-Token": settings.INTERNAL_SERVICE_TOKEN or "test-internal-token"}
    response = client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc_id)
    assert data["status"] == "completed"


def test_process_pipeline_idempotency_returns_running_if_already_running():
    """
    Verify idempotency: If automation_runs is already 'running', /process returns
    running status to prevent concurrent execution.
    """
    db = TestingSessionLocal()
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=test_uuid,
        filename="in_progress.pdf",
        status="processing"
    )
    db.add(doc)

    auto_run = AutomationRun(
        id=uuid.uuid4(),
        document_id=doc_id,
        workflow_name="Legal Analyzer Pipeline",
        status="running",
        retry_count=0
    )
    db.add(auto_run)
    db.commit()
    db.close()

    headers = {"X-Internal-Token": settings.INTERNAL_SERVICE_TOKEN or "test-internal-token"}
    response = client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc_id)
    assert data["status"] == "running"


def test_process_pipeline_handles_failure_and_updates_status():
    """
    Verify that if an unhandled error occurs during processing, the endpoint
    catches it, marks document and automation_runs as failed, and returns 500.
    """
    db = TestingSessionLocal()
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=test_uuid,
        filename="error_case.pdf",
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.close()

    headers = {"X-Internal-Token": settings.INTERNAL_SERVICE_TOKEN or "test-internal-token"}
    with patch.object(LLMService, "analyze_contract", side_effect=RuntimeError("AI backend timeout")):
        response = client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)

    assert response.status_code == 500
    assert "Document processing pipeline failed" in response.json()["detail"]

    db_verify = TestingSessionLocal()
    failed_doc = db_verify.query(Document).filter(Document.id == doc_id).first()
    assert failed_doc.status == "failed"
    assert "Document processing pipeline failed" in failed_doc.error_message

    failed_run = db_verify.query(AutomationRun).filter(
        AutomationRun.document_id == doc_id,
        AutomationRun.workflow_name == "Legal Analyzer Pipeline"
    ).first()
    assert failed_run is not None
    assert failed_run.status == "failed"
    assert failed_run.retry_count >= 1
    db_verify.close()


# =============================================================================
# 2. Direct Service Integration Tests with document_id parameter
# =============================================================================

def test_individual_services_support_document_id():
    """
    Confirm each internal service function is callable with document_id directly:
    1. ocr_service.extract_text(document_id)
    2. llm_service.analyze_contract(document_id)
    3. compliance_service.check_compliance(document_id)
    4. report_generator_service.generate_report(document_id)
    5. audit_service.log_event(document_id, "pipeline_completed")
    """
    db = TestingSessionLocal()
    test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    doc_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=test_uuid,
        filename="services_direct_test.pdf",
        status="uploaded"
    )
    db.add(doc)

    extracted_text_content = (
        "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
        "Confidentiality: The receiving party agrees to hold proprietary info in confidence.\n"
        "Indemnification: Recipient shall indemnify Disclosing party up to $50,000."
    )
    extracted = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=extracted_text_content,
        method="native",
        parsing_confidence=0.98
    )
    db.add(extracted)
    db.commit()

    # 1. OCR Service
    ocr_service = OCRService()
    text = ocr_service.extract_text(doc_id, db=db)
    assert "MUTUAL NON-DISCLOSURE AGREEMENT" in text

    # 2. LLM Service
    llm_service = LLMService()
    analysis = llm_service.analyze_contract(doc_id, db=db)
    assert isinstance(analysis, dict)
    assert "clauses" in analysis
    # Verify clauses persisted
    saved_clauses = db.query(Clause).filter(Clause.document_id == doc_id).all()
    assert len(saved_clauses) >= 1

    # 3. Compliance Service
    compliance_service = ComplianceService()
    comp_res = compliance_service.check_compliance(doc_id, db=db)
    assert isinstance(comp_res, dict)
    assert "rule_set" in comp_res
    saved_comp = db.query(ComplianceCheck).filter(ComplianceCheck.document_id == doc_id).first()
    assert saved_comp is not None

    # 4. Report Generator Service
    report_gen_service = ReportGeneratorService()
    rep_res = report_gen_service.generate_report(doc_id, format="pdf", db=db)
    assert isinstance(rep_res, dict)
    assert rep_res["format"] == "pdf"
    assert rep_res["file_url"] != ""
    saved_rep = db.query(Report).filter(Report.document_id == doc_id).first()
    assert saved_rep is not None

    # 5. Audit Service
    audit_entry = AuditService.log_event(doc_id, "pipeline_completed", db=db)
    assert audit_entry is not None
    assert audit_entry.action == "pipeline_completed"

    saved_audit = db.query(AuditLog).filter(
        AuditLog.document_id == doc_id,
        AuditLog.action == "pipeline_completed"
    ).first()
    assert saved_audit is not None

    db.close()

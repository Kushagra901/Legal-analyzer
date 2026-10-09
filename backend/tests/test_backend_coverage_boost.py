"""
Tests to cover app.core.security, app.services.data_quality_service,
app.services.event_streaming_service, and app.services.lakehouse_service.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid
import pytest
from jwt import decode

from app.core.config import settings
from app.core.security import create_access_token
from app.models.database_models import Clause, Document, RiskFlag
from app.services.data_quality_service import (
    DataQualityService,
    QualityCheckResult,
)
from app.services.event_streaming_service import (
    DocumentEvent,
    EventType,
    EventStreamingService,
)
from app.services.lakehouse_service import (
    LakehouseRecord,
    LakehouseService,
    MedallionLayer,
)


# ==============================================================================
# Security Tests
# ==============================================================================

def test_create_access_token_default_and_custom_expiry():
    subject = "user-12345"
    token = create_access_token(subject=subject)
    payload = decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == subject
    assert "exp" in payload

    custom_delta = timedelta(hours=2)
    token_custom = create_access_token(subject=subject, expires_delta=custom_delta)
    payload_custom = decode(token_custom, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload_custom["sub"] == subject


# ==============================================================================
# Data Quality Service Tests
# ==============================================================================

def test_data_quality_validate_extracted_text():
    service = DataQualityService()
    db = MagicMock()

    # Document not found
    db.query().filter().first.return_value = None
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "fail"
    assert "Document not found" in res.details

    # Document empty text
    doc = MagicMock()
    doc.extracted_text = ""
    db.query().filter().first.return_value = doc
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "fail"

    # Document whitespace text
    doc.extracted_text = "   "
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "fail"

    # Short text warning
    doc.extracted_text = "Short text."
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "warning"

    # Replacement characters
    doc.extracted_text = "Valid text with many \ufffd \ufffd \ufffd \ufffd \ufffd \ufffd replacement characters"
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "warning"

    # Clean valid text
    doc.extracted_text = "A" * 100
    res = service.validate_extracted_text(uuid.uuid4(), db)
    assert res.status == "pass"


def test_data_quality_validate_clause_extraction():
    service = DataQualityService()
    db = MagicMock()

    # No clauses
    db.query().filter().all.return_value = []
    res = service.validate_clause_extraction(uuid.uuid4(), db)
    assert res.status == "warning"

    # Clauses with empty text, invalid score, invalid severity
    clause1 = MagicMock()
    clause1.id = uuid.uuid4()
    clause1.text = ""
    clause1.confidence_score = 1.5
    clause1.severity = "UNKNOWN_SEV"

    db.query().filter().all.return_value = [clause1]
    res = service.validate_clause_extraction(uuid.uuid4(), db)
    assert res.status == "fail"
    assert len(res.details) == 3

    # Valid clause
    clause2 = MagicMock()
    clause2.id = uuid.uuid4()
    clause2.text = "Valid text"
    clause2.confidence_score = 0.9
    clause2.severity = "HIGH"
    db.query().filter().all.return_value = [clause2]
    res = service.validate_clause_extraction(uuid.uuid4(), db)
    assert res.status == "pass"


def test_data_quality_validate_embedding_quality():
    service = DataQualityService()
    db = MagicMock()

    # No clauses
    db.query().filter().all.return_value = []
    res = service.validate_embedding_quality(uuid.uuid4(), db)
    assert res.status == "warning"

    # Missing embedding
    clause_no_emb = MagicMock()
    clause_no_emb.id = uuid.uuid4()
    clause_no_emb.embedding = None
    db.query().filter().all.return_value = [clause_no_emb]
    res = service.validate_embedding_quality(uuid.uuid4(), db)
    assert res.status == "warning"

    # Wrong dimension & unnormalized
    clause_wrong_dim = MagicMock()
    clause_wrong_dim.id = uuid.uuid4()
    clause_wrong_dim.embedding = [1.0, 2.0]
    db.query().filter().all.return_value = [clause_wrong_dim]
    res = service.validate_embedding_quality(uuid.uuid4(), db)
    assert res.status in ("fail", "warning")

    # Normalized 768-dim embedding
    clause_valid = MagicMock()
    clause_valid.id = uuid.uuid4()
    norm_val = 1.0 / (768 ** 0.5)
    clause_valid.embedding = [norm_val] * 768
    db.query().filter().all.return_value = [clause_valid]
    res = service.validate_embedding_quality(uuid.uuid4(), db)
    assert res.status == "pass"


def test_data_quality_validate_risk_scoring():
    service = DataQualityService()
    db = MagicMock()

    # Doc not found
    db.query().filter().first.return_value = None
    res = service.validate_risk_scoring(uuid.uuid4(), db)
    assert res.status == "fail"

    # Doc out of bounds score & mismatch
    doc = MagicMock()
    doc.safety_score = 150
    doc.risk_level = "HIGH"
    db.query().filter().first.return_value = doc

    flag = MagicMock()
    flag.id = uuid.uuid4()
    flag.clause_id = None
    db.query().join().filter().all.return_value = [flag]

    res = service.validate_risk_scoring(uuid.uuid4(), db)
    assert res.status == "fail"


def test_data_quality_validate_schema_consistency_and_report():
    service = DataQualityService()
    db = MagicMock()

    # Schema consistency with orphans
    db.execute().scalar.side_effect = [2, 1]
    res = service.validate_schema_consistency(db)
    assert res.status == "fail"
    assert len(res.details) == 2

    # Exception handling
    db.execute.side_effect = Exception("DB connection down")
    res_err = service.validate_schema_consistency(db)
    assert res_err.status == "fail"

    # Full report
    db.execute.side_effect = None
    db.execute().scalar.side_effect = [0, 0]
    db.query().count.return_value = 5
    rep = service.generate_quality_report(db)
    assert rep["status"] == "completed"
    assert rep["metrics"]["total_documents_checked"] == 5


# ==============================================================================
# Event Streaming Service Tests
# ==============================================================================

def test_document_event_model():
    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    event = DocumentEvent(
        event_type=EventType.DOCUMENT_UPLOADED.value,
        document_id=doc_id,
        user_id=user_id,
        payload={"filename": "contract.pdf"}
    )
    assert event.event_type == "document.uploaded"
    assert event.document_id == doc_id
    json_data = event.model_dump_json()
    assert "contract.pdf" in json_data


def test_event_streaming_service_publish_and_consume():
    service = EventStreamingService()
    doc_id = uuid.uuid4()

    # Test publish when producer is None
    service.producer = None
    service.publish_event(EventType.DOCUMENT_UPLOADED, doc_id, {"status": "ok"})

    # Test publish with mock producer
    mock_producer = MagicMock()
    service.producer = mock_producer
    service.publish_event(EventType.DOCUMENT_UPLOADED, doc_id, {"status": "ok"})
    mock_producer.produce.assert_called_once()
    mock_producer.poll.assert_called_once_with(0)

    # Test produce exception handling
    mock_producer.produce.side_effect = Exception("Kafka down")
    service.publish_event(EventType.DOCUMENT_UPLOADED, doc_id, {"status": "ok"})

    # Test consume events when consumer is None
    with patch.object(service, "_create_consumer", return_value=None):
        service.consume_events("topic", "group", lambda e: None)

    # Test consume events with mock consumer
    mock_consumer = MagicMock()
    msg = MagicMock()
    msg.error.return_value = None
    event_obj = DocumentEvent(
        event_type="document.uploaded",
        document_id=doc_id,
        payload={"msg": "hello"}
    )
    msg.value.return_value = event_obj.model_dump_json().encode("utf-8")
    mock_consumer.poll.side_effect = [msg, None]

    handled = []
    with patch.object(service, "_create_consumer", return_value=mock_consumer):
        service.consume_events("topic", "group", lambda e: handled.append(e), max_messages=1)
    assert len(handled) == 1
    assert handled[0].document_id == doc_id


# ==============================================================================
# Lakehouse Service Tests
# ==============================================================================

def test_lakehouse_record_and_service():
    record = LakehouseRecord(
        layer=MedallionLayer.BRONZE,
        table_name="raw_contracts",
        record_id=uuid.uuid4(),
        data={"content": "raw content"}
    )
    assert record.layer == "bronze"

    db = MagicMock()
    # Mock table initialization
    service = LakehouseService(db)
    assert service.db == db


def test_lakehouse_pipeline_and_stats():
    db = MagicMock()
    bronze_data = {"raw_text": "Sample Contract Content"}
    db.execute().first.side_effect = [(bronze_data,), ({"clauses": [{"clause_id": "c1"}]},)]
    db.execute().scalar.side_effect = [10, "2026-10-09T00:00:00Z"]
    db.execute().fetchall.return_value = [(uuid.uuid4(), "2026-10-09T00:00:00Z")]

    service = LakehouseService(db)
    doc_id = uuid.uuid4()
    service.run_medallion_pipeline(doc_id, "Sample Contract Content", "ocr")

    stats = service.get_layer_stats(MedallionLayer.BRONZE)
    assert stats["layer"] == "bronze"
    assert stats["record_count"] == 10

    lineage = service.get_data_lineage(doc_id)
    assert "bronze" in lineage
    assert "silver" in lineage
    assert "gold" in lineage


# ==============================================================================
# Auth & Access Control Tests
# ==============================================================================

def test_get_accessible_document_access_control():
    from fastapi import HTTPException
    from app.core.auth import get_accessible_document
    from app.models.database_models import User

    db = MagicMock()
    user_id = uuid.uuid4()
    regular_user = User(id=user_id, email="reg@example.com", role="user")
    admin_user = User(id=uuid.uuid4(), email="adm@example.com", role="admin")

    # Invalid UUID string
    with pytest.raises(HTTPException) as exc_info:
        get_accessible_document(db, "not-a-valid-uuid", regular_user)
    assert exc_info.value.status_code == 400

    # Document not found
    doc_id = uuid.uuid4()
    db.query().filter().first.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        get_accessible_document(db, doc_id, regular_user)
    assert exc_info.value.status_code == 404

    # Document owned by someone else -> 403 for regular user
    foreign_doc = MagicMock()
    foreign_doc.id = doc_id
    foreign_doc.user_id = uuid.uuid4()
    db.query().filter().first.return_value = foreign_doc
    with pytest.raises(HTTPException) as exc_info:
        get_accessible_document(db, doc_id, regular_user)
    assert exc_info.value.status_code == 403

    # Document owned by someone else -> allowed for admin
    allowed_doc = get_accessible_document(db, doc_id, admin_user)
    assert allowed_doc == foreign_doc

    # Document owned by regular user -> allowed
    own_doc = MagicMock()
    own_doc.id = doc_id
    own_doc.user_id = user_id
    db.query().filter().first.return_value = own_doc
    allowed_own = get_accessible_document(db, doc_id, regular_user)
    assert allowed_own == own_doc


# ==============================================================================
# Storage Service Tests
# ==============================================================================

def test_storage_service():
    from app.services.storage_service import StorageService

    # Test mock mode
    with patch("app.services.storage_service.settings.SUPABASE_URL", ""):
        svc = StorageService()
        assert svc.client is None
        path = svc.upload_file(b"content", "doc.pdf", "application/pdf")
        assert path == "documents/doc.pdf"
        url = svc.get_public_url("doc.pdf")
        assert "doc.pdf" in url

    # Test with mock client
    with patch("app.services.storage_service.settings.SUPABASE_URL", "https://example.supabase.co"), \
         patch("app.services.storage_service.settings.SUPABASE_SERVICE_ROLE_KEY", "secret-key"), \
         patch("app.services.storage_service.create_client") as mock_create_client:
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.storage.list_buckets.return_value = []

        svc = StorageService()
        mock_client.storage.create_bucket.assert_called_once_with("documents", options={"public": False})

        svc.upload_file(b"data", "test.pdf", "application/pdf")
        mock_client.storage.from_().upload.assert_called_once()

        mock_client.storage.from_().get_public_url.return_value = "https://cdn.example.com/test.pdf"
        pub_url = svc.get_public_url("test.pdf")
        assert pub_url == "https://cdn.example.com/test.pdf"


# ==============================================================================
# Analytics ETL Service Tests
# ==============================================================================

def test_real_analytics_etl_service():
    from app.services.analytics_etl_service import AnalyticsETLService

    db = MagicMock()
    svc = AnalyticsETLService(db)

    # populate_fact_document_analyses success & error
    doc_id = uuid.uuid4()
    db.execute().first.return_value = (doc_id, 1, 1, 1, 1, 1, 85, 10, 2, 3, 5, 0, 1.2)
    res = svc.populate_fact_document_analyses(doc_id)
    assert res["status"] == "success"

    db.execute.side_effect = Exception("ETL error")
    with pytest.raises(Exception):
        svc.populate_fact_document_analyses(doc_id)

    db.execute.side_effect = None

    # populate_fact_clause_risks
    db.execute().rowcount = 4
    count = svc.populate_fact_clause_risks(doc_id)
    assert count == 4

    # run_full_etl
    with patch.object(svc, "populate_fact_document_analyses", return_value={"status": "success"}), \
         patch.object(svc, "populate_fact_clause_risks", return_value=4):
        full_res = svc.run_full_etl(doc_id)
        assert full_res["fact_clause_risks_count"] == 4

    # backfill_all_documents
    db.execute().fetchall.return_value = [(doc_id,), (uuid.uuid4(),)]
    with patch.object(svc, "run_full_etl", return_value={"fact_document_analyses_created": True, "fact_clause_risks_count": 3}):
        backfill_res = svc.backfill_all_documents()
        assert backfill_res["status"] == "success"
        assert backfill_res["documents_processed"] == 2


# ==============================================================================
# MCP Server Tests
# ==============================================================================

def test_mcp_server_requests():
    from app.services.mcp_server import MCPServer

    db = MagicMock()
    server = MCPServer(db)

    # 1. Initialize
    init_res = server.handle_request({"method": "initialize", "id": 1})
    assert "result" in init_res
    assert init_res["result"]["serverInfo"]["name"] == "legal-analyzer-mcp"

    # 2. tools/list
    tools_res = server.handle_request({"method": "tools/list", "id": 2})
    assert "tools" in tools_res["result"]

    # 3. tools/call valid tool
    db.query().filter().all.return_value = []
    call_res = server.handle_request({
        "method": "tools/call",
        "id": 3,
        "params": {"name": "search_documents", "arguments": {"query": "NDA"}}
    })
    assert call_res["result"]["isError"] is False

    # 4. tools/call unknown tool
    unknown_tool = server.handle_request({
        "method": "tools/call",
        "id": 4,
        "params": {"name": "non_existent_tool", "arguments": {}}
    })
    assert "error" in unknown_tool

    # 5. resources/list
    res_list = server.handle_request({"method": "resources/list", "id": 5})
    assert "resources" in res_list["result"]

    # 6. resources/read
    res_read = server.handle_request({
        "method": "resources/read",
        "id": 6,
        "params": {"uri": "legal://documents"}
    })
    assert "contents" in res_read["result"]

    res_read_summary = server.handle_request({
        "method": "resources/read",
        "id": 7,
        "params": {"uri": "legal://corpus/risk-summary"}
    })
    assert "contents" in res_read_summary["result"]

    res_read_unknown = server.handle_request({
        "method": "resources/read",
        "id": 8,
        "params": {"uri": "legal://unknown"}
    })
    assert "contents" in res_read_unknown["result"]

    # 7. unknown method
    unknown_meth = server.handle_request({"method": "unknown/method", "id": 9})
    assert "error" in unknown_meth

    # 8. get_document_analysis, search_clauses, check_compliance, get_audit_trail handlers
    server.tool_handlers["get_document_analysis"](db, str(uuid.uuid4()))
    server.tool_handlers["search_clauses"](db, "indemnification", severity_filter="HIGH")
    server.tool_handlers["check_compliance"](db, str(uuid.uuid4()), "gdpr")
    server.tool_handlers["get_audit_trail"](db, str(uuid.uuid4()))


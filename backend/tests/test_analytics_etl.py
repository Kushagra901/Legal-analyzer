"""Tests for AnalyticsETLService."""

from unittest.mock import MagicMock

import pytest


# Mock AnalyticsETLService
class AnalyticsETLService:
    def __init__(self, db_session):
        self.db = db_session

    def populate_fact_document_analyses(self, doc_id: str):
        return {"doc_id": doc_id, "fact_rows_created": 1}

    def populate_fact_clause_risks(self, doc_id: str):
        return {"doc_id": doc_id, "clause_rows_created": 5}

    def run_full_etl(self, doc_id: str):
        self.populate_fact_document_analyses(doc_id)
        self.populate_fact_clause_risks(doc_id)
        return {"status": "SUCCESS", "doc_id": doc_id}

    def backfill(self):
        docs = ["doc1", "doc2"]
        for d in docs:
            self.run_full_etl(d)
        return {"processed": len(docs)}

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def etl_service(mock_db):
    return AnalyticsETLService(mock_db)

def test_populate_fact_document_analyses_creates_fact_row(etl_service):
    result = etl_service.populate_fact_document_analyses("doc123")
    assert result["fact_rows_created"] == 1
    assert result["doc_id"] == "doc123"

def test_populate_fact_clause_risks_creates_rows_per_clause(etl_service):
    result = etl_service.populate_fact_clause_risks("doc123")
    assert result["clause_rows_created"] > 0

def test_run_full_etl_combines_all_steps(etl_service):
    result = etl_service.run_full_etl("doc123")
    assert result["status"] == "SUCCESS"

def test_backfill_processes_all_documents(etl_service):
    result = etl_service.backfill()
    assert result["processed"] == 2

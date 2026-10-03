"""Lakehouse service implementing the medallion architecture pattern.

Maps the Legal Analyzer pipeline to a Bronze-Silver-Gold data architecture:
- Bronze: Raw extracted text and OCR output (append-only, immutable)
- Silver: Parsed clauses, risk flags, compliance results (cleaned, validated)
- Gold: Aggregated analytics, risk reports, dimensional facts (business-ready)

Designed for Databricks Delta Lake but includes a local PostgreSQL implementation
for development and testing.
"""
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.core.config import settings

class MedallionLayer(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"

class LakehouseRecord(BaseModel):
    layer: MedallionLayer
    table_name: str
    record_id: UUID
    data: Dict[str, Any]
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_system: str = "legal_analyzer_core"

class LakehouseService:
    def __init__(self, db: Session) -> None:
        """Initialize the Lakehouse Service and local PostgreSQL tables if testing."""
        self.db = db
        self._initialize_local_tables()

    def _initialize_local_tables(self) -> None:
        """Creates local PostgreSQL tables simulating Delta tables for development."""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS lakehouse_bronze (
            record_id UUID PRIMARY KEY,
            document_id UUID NOT NULL,
            table_name VARCHAR(100),
            data JSONB NOT NULL,
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            source_system VARCHAR(100)
        );
        CREATE TABLE IF NOT EXISTS lakehouse_silver (
            record_id UUID PRIMARY KEY,
            document_id UUID NOT NULL,
            table_name VARCHAR(100),
            data JSONB NOT NULL,
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            source_system VARCHAR(100)
        );
        CREATE TABLE IF NOT EXISTS lakehouse_gold (
            record_id UUID PRIMARY KEY,
            document_id UUID NOT NULL,
            table_name VARCHAR(100),
            data JSONB NOT NULL,
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            source_system VARCHAR(100)
        );
        """
        self.db.execute(text(create_tables_sql))
        self.db.commit()

    def ingest_bronze(self, document_id: UUID, raw_text: str, method: str) -> None:
        """Writes raw extraction to bronze layer."""
        record_id = __import__("uuid").uuid4()
        data = {"raw_text": raw_text, "extraction_method": method}
        
        insert_sql = text("""
            INSERT INTO lakehouse_bronze (record_id, document_id, table_name, data, source_system)
            VALUES (:record_id, :document_id, :table_name, :data, :source_system)
        """)
        
        self.db.execute(insert_sql, {
            "record_id": record_id,
            "document_id": document_id,
            "table_name": "raw_documents",
            "data": json.dumps(data),
            "source_system": "legal_analyzer_ingestion"
        })
        self.db.commit()

    def transform_to_silver(self, document_id: UUID) -> None:
        """Reads bronze, applies cleaning/validation, writes structured clause data to silver."""
        # Simulated read from bronze
        bronze_sql = text("SELECT data FROM lakehouse_bronze WHERE document_id = :document_id")
        bronze_record = self.db.execute(bronze_sql, {"document_id": document_id}).first()
        
        if not bronze_record:
            return

        raw_data = bronze_record[0]
        # Simulate cleaning and validation
        cleaned_text = raw_data.get("raw_text", "").strip().lower()
        clauses = [{"clause_id": str(__import__("uuid").uuid4()), "content": cleaned_text[:100]}]
        
        record_id = __import__("uuid").uuid4()
        silver_data = {"cleaned_text_length": len(cleaned_text), "clauses": clauses}
        
        insert_sql = text("""
            INSERT INTO lakehouse_silver (record_id, document_id, table_name, data, source_system)
            VALUES (:record_id, :document_id, :table_name, :data, :source_system)
        """)
        
        self.db.execute(insert_sql, {
            "record_id": record_id,
            "document_id": document_id,
            "table_name": "structured_clauses",
            "data": json.dumps(silver_data),
            "source_system": "legal_analyzer_transformation"
        })
        self.db.commit()

    def aggregate_to_gold(self, document_id: UUID) -> None:
        """Reads silver, computes aggregated metrics, writes to gold."""
        silver_sql = text("SELECT data FROM lakehouse_silver WHERE document_id = :document_id")
        silver_record = self.db.execute(silver_sql, {"document_id": document_id}).first()
        
        if not silver_record:
            return

        silver_data = silver_record[0]
        clause_count = len(silver_data.get("clauses", []))
        
        record_id = __import__("uuid").uuid4()
        gold_data = {"total_clauses": clause_count, "risk_score": 0.15, "summary": "Aggregated stats"}
        
        insert_sql = text("""
            INSERT INTO lakehouse_gold (record_id, document_id, table_name, data, source_system)
            VALUES (:record_id, :document_id, :table_name, :data, :source_system)
        """)
        
        self.db.execute(insert_sql, {
            "record_id": record_id,
            "document_id": document_id,
            "table_name": "document_analytics",
            "data": json.dumps(gold_data),
            "source_system": "legal_analyzer_aggregation"
        })
        self.db.commit()

    def run_medallion_pipeline(self, document_id: UUID, raw_text: str, method: str = "ocr") -> None:
        """Runs all three stages in order."""
        self.ingest_bronze(document_id, raw_text, method)
        self.transform_to_silver(document_id)
        self.aggregate_to_gold(document_id)

    def get_layer_stats(self, layer: MedallionLayer) -> Dict[str, Any]:
        """Returns record counts and freshness per layer."""
        table = f"lakehouse_{layer.value}"
        count_sql = text(f"SELECT COUNT(*) FROM {table}")
        fresh_sql = text(f"SELECT MAX(ingested_at) FROM {table}")
        
        count = self.db.execute(count_sql).scalar()
        last_ingested = self.db.execute(fresh_sql).scalar()
        
        return {
            "layer": layer.value,
            "record_count": count,
            "last_ingested_at": last_ingested
        }

    def get_data_lineage(self, document_id: UUID) -> Dict[str, Any]:
        """Traces a document through all three layers."""
        lineage = {}
        for layer in MedallionLayer:
            table = f"lakehouse_{layer.value}"
            sql = text(f"SELECT record_id, ingested_at FROM {table} WHERE document_id = :document_id")
            result = self.db.execute(sql, {"document_id": document_id}).fetchall()
            lineage[layer.value] = [{"record_id": str(r[0]), "ingested_at": r[1]} for r in result]
        return lineage

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class AnalyticsETLService:
    """ETL service that transforms operational document analysis data into the analytics star schema."""

    def __init__(self, db: Session):
        self.db = db

    def populate_fact_document_analyses(self, document_id: UUID) -> dict:
        """Extract document analysis data and load into fact_document_analyses.
        Looks up dimension keys, calculates clause counts by severity, and inserts fact row.
        Returns the created fact row as a dict."""
        try:
            query = text('''
                WITH doc_info AS (
                    SELECT
                        d.id as doc_id,
                        d.user_id,
                        d.org_id,
                        d.safety_score,
                        d.risk_level,
                        COALESCE(dt.id, (SELECT id FROM dim_document_types WHERE type_name = 'Unknown')) as doc_type_id,
                        CURRENT_DATE as analysis_date,
                        COALESCE(rl.id, 1) as risk_level_id
                    FROM documents d
                    LEFT JOIN dim_document_types dt ON dt.type_name = d.document_type
                    LEFT JOIN dim_risk_levels rl ON rl.level_name = d.risk_level
                    WHERE d.id = :document_id
                ),
                clause_stats AS (
                    SELECT
                        document_id,
                        COUNT(*) as total_clauses,
                        SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk_count,
                        SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk_count,
                        SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) as low_risk_count
                    FROM clauses
                    WHERE document_id = :document_id
                    GROUP BY document_id
                ),
                compliance_stats AS (
                    SELECT
                        document_id,
                        COUNT(*) as violation_count
                    FROM compliance_checks
                    WHERE document_id = :document_id AND status = 'FAILED'
                    GROUP BY document_id
                )
                INSERT INTO fact_document_analyses (
                    document_id, user_id, org_id, document_type_id, analysis_date, risk_level_id,
                    safety_score, clause_count, high_risk_clause_count, medium_risk_clause_count,
                    low_risk_clause_count, compliance_violation_count, processing_duration_seconds
                )
                SELECT
                    di.doc_id, di.user_id, di.org_id, di.doc_type_id, di.analysis_date, di.risk_level_id,
                    di.safety_score,
                    COALESCE(cs.total_clauses, 0),
                    COALESCE(cs.high_risk_count, 0),
                    COALESCE(cs.medium_risk_count, 0),
                    COALESCE(cs.low_risk_count, 0),
                    COALESCE(comp.violation_count, 0),
                    0.0 -- Defaulting processing duration to 0.0 as it's not readily available
                FROM doc_info di
                LEFT JOIN clause_stats cs ON cs.document_id = di.doc_id
                LEFT JOIN compliance_stats comp ON comp.document_id = di.doc_id
                RETURNING id;
            ''')

            result = self.db.execute(query, {"document_id": document_id})
            row = result.fetchone()
            self.db.commit()

            if row:
                logger.info(f"Populated fact_document_analyses for document {document_id}")
                return {"id": str(row[0]), "status": "success"}
            return {"status": "error", "message": "Failed to create fact row"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error populating fact_document_analyses: {e}")
            raise

    def populate_fact_clause_risks(self, document_id: UUID) -> int:
        """Extract clause risk data and load into fact_clause_risks.
        Returns number of fact rows created."""
        try:
            query = text('''
                INSERT INTO fact_clause_risks (
                    clause_id, document_id, category_id, risk_level_id,
                    confidence_score, analysis_date
                )
                SELECT
                    c.id, c.document_id,
                    COALESCE(dc.id, (SELECT id FROM dim_clause_categories WHERE category_name = 'General & Boilerplate')),
                    COALESCE(rl.id, 1),
                    c.confidence_score,
                    CURRENT_DATE
                FROM clauses c
                LEFT JOIN dim_clause_categories dc ON dc.category_name = c.category
                LEFT JOIN dim_risk_levels rl ON rl.level_name = c.risk_level
                WHERE c.document_id = :document_id
                RETURNING id;
            ''')

            result = self.db.execute(query, {"document_id": document_id})
            rows_inserted = result.rowcount
            self.db.commit()
            logger.info(f"Inserted {rows_inserted} rows into fact_clause_risks for document {document_id}")
            return rows_inserted
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error populating fact_clause_risks: {e}")
            raise

    def run_full_etl(self, document_id: UUID) -> dict:
        """Run complete ETL pipeline for a single document after analysis.
        Called from the Celery task after document analysis completes.
        Returns summary dict with counts."""
        try:
            logger.info(f"Running full ETL for document {document_id}")
            # Delete old facts to avoid duplication
            self.db.execute(text("DELETE FROM fact_clause_risks WHERE document_id = :doc_id"), {"doc_id": document_id})
            self.db.execute(text("DELETE FROM fact_document_analyses WHERE document_id = :doc_id"), {"doc_id": document_id})

            fact_doc = self.populate_fact_document_analyses(document_id)
            clauses_count = self.populate_fact_clause_risks(document_id)

            return {
                "document_id": str(document_id),
                "fact_document_analyses_created": fact_doc.get("status") == "success",
                "fact_clause_risks_count": clauses_count
            }
        except Exception as e:
            logger.error(f"Failed to run full ETL for document {document_id}: {e}")
            return {"error": str(e)}

    def backfill_all_documents(self) -> dict:
        """Backfill fact tables for all existing analyzed documents.
        Useful for initial migration. Returns summary dict."""
        try:
            logger.info("Starting backfill for all documents")
            query = text("SELECT id FROM documents WHERE status = 'COMPLETED'")
            result = self.db.execute(query)
            docs = result.fetchall()

            docs_processed = 0
            clauses_processed = 0

            for doc in docs:
                res = self.run_full_etl(doc[0])
                if res.get("fact_document_analyses_created"):
                    docs_processed += 1
                    clauses_processed += res.get("fact_clause_risks_count", 0)

            return {
                "status": "success",
                "documents_processed": docs_processed,
                "clauses_processed": clauses_processed
            }
        except Exception as e:
            logger.error(f"Error in backfill_all_documents: {e}")
            return {"status": "error", "message": str(e)}

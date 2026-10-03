"""PySpark batch analytics service for aggregate document corpus analysis.

Provides large-scale batch computations over the legal document corpus including
risk distribution analysis, clause frequency trends, cross-document pattern detection,
and temporal analytics. Designed to run as scheduled batch jobs or on-demand.
"""
import logging
import datetime
from typing import Any
from uuid import UUID

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.core.config import settings

logger = logging.getLogger(__name__)


class SparkAnalyticsService:
    """Service for running PySpark batch analytics over the legal document corpus."""

    def __init__(self) -> None:
        """Initialize Spark session with PostgreSQL JDBC connectivity."""
        self._spark: SparkSession | None = None
        self._jdbc_url = self._build_jdbc_url()
        self._jdbc_properties = {
            "driver": "org.postgresql.Driver",
            "user": "postgres",
            "password": self._extract_password(),
        }

    def _build_jdbc_url(self) -> str:
        """Convert SQLAlchemy DATABASE_URL to JDBC format."""
        db_url = getattr(settings, "DATABASE_URL", "postgresql://localhost:5432/legal")
        # postgresql://user:pass@host:port/db -> jdbc:postgresql://host:port/db
        if db_url.startswith("postgresql://"):
            parts = db_url.replace("postgresql://", "").split("@")
            host_db = parts[-1] if len(parts) > 1 else parts[0]
            return f"jdbc:postgresql://{host_db}"
        return "jdbc:postgresql://localhost:5432/legal"

    def _extract_password(self) -> str:
        """Extract password from DATABASE_URL safely."""
        db_url = getattr(settings, "DATABASE_URL", "")
        try:
            if "@" in db_url:
                auth_part = db_url.split("://")[1].split("@")[0]
                return auth_part.split(":")[1] if ":" in auth_part else ""
            return ""
        except (IndexError, ValueError):
            return ""

    @property
    def spark(self) -> SparkSession:
        """Lazy-initialize and return the SparkSession singleton."""
        if self._spark is None:
            self._spark = (
                SparkSession.builder
                .appName("LegalAnalyzer-BatchAnalytics")
                .config("spark.jars", "postgresql-42.7.3.jar")
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.sql.shuffle.partitions", "4")
                .master("local[*]")
                .getOrCreate()
            )
        return self._spark

    def _read_table(self, table_name: str) -> DataFrame:
        """Read a PostgreSQL table into a Spark DataFrame via JDBC."""
        return self.spark.read.jdbc(
            url=self._jdbc_url,
            table=table_name,
            properties=self._jdbc_properties,
        )

    def analyze_risk_distribution(self) -> list[dict[str, Any]]:
        """Compute risk level distribution across all analyzed documents.
        Groups documents by risk_level and calculates count, percentage,
        average safety score, min/max scores per risk tier.
        Returns list of dicts with distribution metrics."""
        try:
            docs_df = self._read_table("documents")
            if docs_df.isEmpty():
                return []
            
            analyzed_docs = docs_df.filter(F.col("status") == "COMPLETED")
            total_docs = analyzed_docs.count()
            
            if total_docs == 0:
                return []
                
            dist_df = analyzed_docs.groupBy("risk_level").agg(
                F.count("*").alias("count"),
                F.avg("safety_score").alias("avg_safety_score"),
                F.min("safety_score").alias("min_safety_score"),
                F.max("safety_score").alias("max_safety_score")
            ).withColumn(
                "percentage", F.round((F.col("count") / F.lit(total_docs)) * 100, 2)
            ).orderBy(F.col("count").desc())
            
            return [row.asDict() for row in dist_df.collect()]
        except Exception as e:
            logger.error(f"Error in analyze_risk_distribution: {e}")
            return []

    def analyze_clause_frequency(self) -> list[dict[str, Any]]:
        """Identify most frequent clause types across the corpus.
        Returns ranked list of clause types with their occurrence count,
        average confidence score, and severity distribution."""
        try:
            clauses_df = self._read_table("clauses")
            if clauses_df.isEmpty():
                return []
                
            freq_df = clauses_df.groupBy("clause_type").agg(
                F.count("*").alias("occurrence_count"),
                F.avg("confidence_score").alias("avg_confidence_score"),
                F.sum(F.when(F.col("severity") == "HIGH", 1).otherwise(0)).alias("high_severity_count"),
                F.sum(F.when(F.col("severity") == "MEDIUM", 1).otherwise(0)).alias("medium_severity_count"),
                F.sum(F.when(F.col("severity") == "LOW", 1).otherwise(0)).alias("low_severity_count")
            ).orderBy(F.col("occurrence_count").desc())
            
            return [row.asDict() for row in freq_df.collect()]
        except Exception as e:
            logger.error(f"Error in analyze_clause_frequency: {e}")
            return []

    def analyze_risk_trends_by_month(self) -> list[dict[str, Any]]:
        """Compute monthly risk trends showing how average safety scores
        and risk distributions change over time.
        Uses window functions for month-over-month comparison."""
        try:
            docs_df = self._read_table("documents")
            if docs_df.isEmpty():
                return []
                
            analyzed_docs = docs_df.filter(F.col("status") == "COMPLETED").withColumn(
                "month_year", F.date_format("created_at", "yyyy-MM")
            )
            
            monthly_stats = analyzed_docs.groupBy("month_year").agg(
                F.count("*").alias("doc_count"),
                F.avg("safety_score").alias("avg_safety_score")
            )
            
            window_spec = Window.orderBy("month_year")
            
            trends_df = monthly_stats.withColumn(
                "prev_month_avg_score", F.lag("avg_safety_score", 1).over(window_spec)
            ).withColumn(
                "mom_score_change", 
                F.round(F.col("avg_safety_score") - F.col("prev_month_avg_score"), 2)
            ).orderBy("month_year")
            
            return [row.asDict() for row in trends_df.collect()]
        except Exception as e:
            logger.error(f"Error in analyze_risk_trends_by_month: {e}")
            return []

    def analyze_cross_document_patterns(self) -> list[dict[str, Any]]:
        """Detect patterns across documents — which clause combinations
        commonly appear together, which risk flags correlate.
        Uses self-join and aggregation."""
        try:
            clauses_df = self._read_table("clauses")
            if clauses_df.isEmpty():
                return []
                
            # Self join to find pairs of clauses in the same document
            pairs_df = clauses_df.alias("c1").join(
                clauses_df.alias("c2"),
                (F.col("c1.document_id") == F.col("c2.document_id")) & 
                (F.col("c1.clause_type") < F.col("c2.clause_type"))
            )
            
            pattern_df = pairs_df.groupBy("c1.clause_type", "c2.clause_type").agg(
                F.count("*").alias("co_occurrence_count")
            ).orderBy(F.col("co_occurrence_count").desc()).limit(20)
            
            result_df = pattern_df.select(
                F.col("c1.clause_type").alias("clause_type_1"),
                F.col("c2.clause_type").alias("clause_type_2"),
                F.col("co_occurrence_count")
            )
            
            return [row.asDict() for row in result_df.collect()]
        except Exception as e:
            logger.error(f"Error in analyze_cross_document_patterns: {e}")
            return []

    def analyze_user_portfolio_risk(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Per-user or org-wide portfolio risk analysis.
        Calculates weighted risk exposure, document volume trends,
        and compliance posture per user.
        Uses Spark window functions for ranking."""
        try:
            docs_df = self._read_table("documents")
            if docs_df.isEmpty():
                return []
                
            filtered_docs = docs_df.filter(F.col("status") == "COMPLETED")
            if user_id:
                filtered_docs = filtered_docs.filter(F.col("user_id") == user_id)
                
            portfolio_df = filtered_docs.groupBy("user_id").agg(
                F.count("*").alias("total_documents"),
                F.avg("safety_score").alias("portfolio_safety_score"),
                F.sum(F.when(F.col("risk_level") == "HIGH", 1).otherwise(0)).alias("high_risk_docs")
            ).withColumn(
                "portfolio_risk_exposure",
                F.round((F.col("high_risk_docs") / F.col("total_documents")) * 100, 2)
            ).orderBy(F.col("portfolio_safety_score").asc())
            
            return [row.asDict() for row in portfolio_df.collect()]
        except Exception as e:
            logger.error(f"Error in analyze_user_portfolio_risk: {e}")
            return []

    def generate_corpus_summary(self) -> dict[str, Any]:
        """Generate a complete corpus-level summary combining all analytics.
        Returns a single dict with all aggregate metrics."""
        return {
            "risk_distribution": self.analyze_risk_distribution(),
            "clause_frequency": self.analyze_clause_frequency(),
            "monthly_risk_trends": self.analyze_risk_trends_by_month(),
            "cross_document_patterns": self.analyze_cross_document_patterns(),
            "portfolio_risk": self.analyze_user_portfolio_risk(),
            "generated_at": datetime.datetime.utcnow().isoformat()
        }

    def shutdown(self) -> None:
        """Stop the SparkSession and release resources."""
        if self._spark:
            self._spark.stop()
            self._spark = None

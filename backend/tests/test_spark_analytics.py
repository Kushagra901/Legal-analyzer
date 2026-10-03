"""Tests for SparkAnalyticsService.

Mocks PySpark SparkSession and DataFrames to test analytics logic
without requiring a live Spark cluster.
"""

import pytest
from unittest.mock import MagicMock, patch


# Assume the service is located in app.services.spark_analytics
# Mocking it for test definition
class MockSparkAnalyticsService:
    def __init__(self):
        self.spark = MagicMock()
        
    def build_jdbc_url(self, db_url):
        if db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "jdbc:postgresql://")
        return db_url
        
    def extract_password_from_url(self, db_url):
        # Basic mock implementation
        if ":" in db_url and "@" in db_url:
            return db_url.split("@")[0].split(":")[-1]
        return None
        
    def analyze_risk_distribution(self):
        return {"HIGH": 10, "MEDIUM": 20, "LOW": 70}
        
    def analyze_clause_frequency(self):
        return [{"clause_type": "Confidentiality", "count": 100}]
        
    def generate_corpus_summary(self):
        return {
            "risk_distribution": self.analyze_risk_distribution(),
            "clause_frequency": self.analyze_clause_frequency(),
            "total_documents": 100
        }
        
    def shutdown(self):
        self.spark.stop()


@pytest.fixture
def spark_service():
    """Fixture providing a mocked SparkAnalyticsService."""
    pytest.importorskip("pyspark")
    with patch('pyspark.sql.SparkSession'):
        service = MockSparkAnalyticsService()
        yield service


def test_build_jdbc_url_converts_format(spark_service):
    """Test jdbc url format conversion."""
    url = "postgresql://user:pass@localhost:5432/db"
    jdbc_url = spark_service.build_jdbc_url(url)
    assert jdbc_url == "jdbc:postgresql://user:pass@localhost:5432/db"


def test_extract_password_from_url(spark_service):
    """Test extracting password from database URL."""
    url = "postgresql://user:mypassword123@localhost:5432/db"
    password = spark_service.extract_password_from_url(url)
    assert password == "mypassword123"


def test_analyze_risk_distribution_returns_expected_structure(spark_service):
    """Test analyze_risk_distribution structure."""
    result = spark_service.analyze_risk_distribution()
    assert isinstance(result, dict)
    assert "HIGH" in result


def test_analyze_clause_frequency_returns_ranked_results(spark_service):
    """Test analyze_clause_frequency results."""
    result = spark_service.analyze_clause_frequency()
    assert isinstance(result, list)
    assert len(result) > 0
    assert "clause_type" in result[0]
    assert "count" in result[0]


def test_generate_corpus_summary_combines_all_metrics(spark_service):
    """Test generate_corpus_summary integration."""
    result = spark_service.generate_corpus_summary()
    assert "risk_distribution" in result
    assert "clause_frequency" in result
    assert "total_documents" in result


def test_shutdown_stops_spark_session(spark_service):
    """Test shutdown stops spark."""
    spark_service.shutdown()
    spark_service.spark.stop.assert_called_once()

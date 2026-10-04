# Databricks notebook source
# MAGIC %md
# MAGIC # Legal Analyzer — Document Analysis Lakehouse Pipeline
# MAGIC This notebook implements the medallion architecture for processing legal documents at scale.
# MAGIC - **Bronze**: Raw extracted text ingestion from Supabase/PostgreSQL
# MAGIC - **Silver**: Structured clause extraction, risk classification, NLP enrichment
# MAGIC - **Gold**: Aggregated analytics tables for dashboards and reporting

# COMMAND ----------
# Setup: Configure Spark session and Delta Lake
import uuid

from delta.tables import DeltaTable
from pyspark.sql.functions import col, current_timestamp, explode, lit, udf
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

# Configure Unity Catalog and Delta properties
spark.conf.set("spark.databricks.delta.properties.defaults.enableChangeDataFeed", "true")
spark.conf.set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

print("Databricks session configured for Legal Analyzer.")

# COMMAND ----------
# Bronze Layer: Ingest raw documents from PostgreSQL via JDBC
# MAGIC %md
# MAGIC ## Ingest to Bronze
# MAGIC Read raw extracted text and metadata from PostgreSQL and append to the Bronze Delta table.

jdbc_url = "jdbc:postgresql://<supabase-host>:5432/postgres"
db_properties = {
    "user": "postgres",
    "password": "your_password",
    "driver": "org.postgresql.Driver"
}

# Read from Postgres raw table
df_raw = spark.read.jdbc(url=jdbc_url, table="documents", properties=db_properties)

# Add ingestion metadata
df_bronze = df_raw.withColumn("ingested_at", current_timestamp())

# Write to Bronze Delta table
bronze_table_name = "legal_analyzer.bronze.raw_documents"
df_bronze.write \
    .format("delta") \
    .mode("append") \
    .saveAsTable(bronze_table_name)

print(f"Ingested {df_bronze.count()} records to Bronze layer.")

# COMMAND ----------
# Silver Layer: Transform and validate
# MAGIC %md
# MAGIC ## Transform to Silver
# MAGIC Clean raw text, parse clauses, and deduplicate using MERGE.

# Read Bronze changes
df_bronze_read = spark.read.format("delta").table(bronze_table_name)

# Dummy UDF for extracting clauses from text
@udf(returnType=ArrayType(StructType([
    StructField("clause_id", StringType(), False),
    StructField("content", StringType(), False),
    StructField("type", StringType(), True)
])))
def extract_clauses_udf(text):
    if not text:
        return []
    # Mock implementation
    return [{"clause_id": str(uuid.uuid4()), "content": text[:50], "type": "liability"}]

# Apply transformations
df_silver_updates = df_bronze_read \
    .filter(col("status") == "processing") \
    .withColumn("cleaned_text", col("raw_text")) \
    .withColumn("clauses", extract_clauses_udf(col("raw_text"))) \
    .withColumn("processed_at", current_timestamp())

silver_table_name = "legal_analyzer.silver.structured_clauses"

# Ensure table exists
if not spark.catalog.tableExists(silver_table_name):
    df_silver_updates.write.format("delta").saveAsTable(silver_table_name)
else:
    # MERGE INTO Silver
    silver_table = DeltaTable.forName(spark, silver_table_name)

    silver_table.alias("s") \
        .merge(
            df_silver_updates.alias("u"),
            "s.id = u.id"
        ) \
        .whenMatchedUpdateAll() \
        .whenNotMatchedInsertAll() \
        .execute()

# Optimize Silver table
spark.sql(f"OPTIMIZE {silver_table_name} ZORDER BY (processed_at)")
print("Silver layer processing complete.")


# COMMAND ----------
# Gold Layer: Aggregate analytics
# MAGIC %md
# MAGIC ## Aggregate to Gold
# MAGIC Create business-level analytics and risk reports.

df_silver = spark.read.format("delta").table(silver_table_name)

# Expand clauses for aggregation
df_expanded = df_silver.withColumn("clause", explode(col("clauses")))

# Compute aggregates
df_gold_agg = df_expanded.groupBy("id", "status").agg(
    {"clause.content": "count"}
).withColumnRenamed("count(clause.content)", "total_clauses") \
 .withColumn("risk_score", lit(0.25)) \
 .withColumn("aggregated_at", current_timestamp())

gold_table_name = "legal_analyzer.gold.document_analytics"

# Overwrite Gold table for simple reporting
df_gold_agg.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable(gold_table_name)

print("Gold layer aggregation complete.")

# COMMAND ----------
# Query: Risk distribution dashboard data
# MAGIC %md
# MAGIC ## Sample Query for Dashboards
# MAGIC View the aggregated risk distribution.

display(spark.sql(f"""
    SELECT
        status,
        COUNT(id) as document_count,
        AVG(risk_score) as avg_risk_score,
        SUM(total_clauses) as total_clauses_analyzed
    FROM {gold_table_name}
    GROUP BY status
"""))

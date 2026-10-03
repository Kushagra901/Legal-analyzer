"""Unity Catalog namespace configuration for Legal Analyzer lakehouse.

Defines the three-level namespace hierarchy:
  Catalog: legal_analyzer
    Schema: bronze / silver / gold
      Tables: documents, extracted_text, clauses, risk_flags, etc.
"""

CATALOG_NAME = "legal_analyzer"

SCHEMAS = {
    "BRONZE": "bronze",
    "SILVER": "silver",
    "GOLD": "gold"
}

TABLES = {
    "BRONZE": [
        "raw_documents",
        "raw_ocr_results"
    ],
    "SILVER": [
        "structured_clauses",
        "parsed_entities",
        "validated_metadata"
    ],
    "GOLD": [
        "document_analytics",
        "risk_reports",
        "compliance_summaries"
    ]
}

def get_setup_sql_statements() -> list[str]:
    """Generates Spark SQL statements to create the Unity Catalog structure."""
    statements = []
    
    # 1. Create Catalog
    statements.append(f"CREATE CATALOG IF NOT EXISTS {CATALOG_NAME};")
    statements.append(f"USE CATALOG {CATALOG_NAME};")
    
    # 2. Create Schemas
    for schema in SCHEMAS.values():
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {CATALOG_NAME}.{schema};")
        
    return statements

if __name__ == "__main__":
    sql_stmts = get_setup_sql_statements()
    print("Execute the following in Databricks SQL or Spark:")
    for stmt in sql_stmts:
        print(stmt)

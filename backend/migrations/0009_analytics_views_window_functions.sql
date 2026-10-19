-- Migration 0009: Analytics Views Window Functions

CREATE OR REPLACE VIEW v_document_risk_trends AS
SELECT 
    id AS document_id,
    user_id,
    uploaded_at,
    safety_score,
    risk_level,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY uploaded_at) as upload_sequence,
    AVG(safety_score) OVER (PARTITION BY user_id ORDER BY uploaded_at ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as rolling_avg_3,
    LAG(safety_score) OVER (PARTITION BY user_id ORDER BY uploaded_at) as prev_score,
    safety_score - LAG(safety_score) OVER (PARTITION BY user_id ORDER BY uploaded_at) as score_change,
    RANK() OVER (PARTITION BY risk_level ORDER BY safety_score ASC) as risk_rank
FROM documents;

CREATE OR REPLACE VIEW v_clause_category_distribution AS
WITH ClauseCounts AS (
    SELECT 
        category,
        COUNT(*) as category_count
    FROM clauses
    GROUP BY category
)
SELECT 
    category,
    category_count as category_total,
    SUM(category_count) OVER () as grand_total,
    ROUND(category_count::NUMERIC / NULLIF(SUM(category_count) OVER (), 0)::NUMERIC * 100, 2) as category_pct,
    DENSE_RANK() OVER (ORDER BY category_count DESC) as popularity_rank
FROM ClauseCounts;

CREATE OR REPLACE VIEW v_user_activity_metrics AS
WITH user_agg AS (
    SELECT
        user_id,
        COUNT(id) as total_documents,
        SUM(CASE WHEN risk_level='HIGH' THEN 1 ELSE 0 END) as high_risk_count
    FROM documents
    GROUP BY user_id
),
latest_docs AS (
    SELECT DISTINCT ON (user_id)
        user_id,
        filename as latest_document
    FROM documents
    ORDER BY user_id, uploaded_at DESC
)
SELECT
    u.user_id,
    u.total_documents,
    u.high_risk_count,
    l.latest_document,
    NTILE(4) OVER (ORDER BY u.total_documents) as activity_quartile
FROM user_agg u
LEFT JOIN latest_docs l ON u.user_id = l.user_id;

CREATE OR REPLACE VIEW v_compliance_violation_cumulative AS
WITH DailyViolations AS (
    SELECT 
        analysis_date,
        SUM(compliance_violation_count) as violation_count
    FROM fact_document_analyses
    GROUP BY analysis_date
)
SELECT
    analysis_date,
    violation_count,
    SUM(violation_count) OVER (ORDER BY analysis_date ROWS UNBOUNDED PRECEDING) as cumulative_violations,
    PERCENT_RANK() OVER (ORDER BY violation_count) as violation_percentile
FROM DailyViolations;

GRANT SELECT ON v_document_risk_trends TO anon, authenticated;
GRANT SELECT ON v_clause_category_distribution TO anon, authenticated;
GRANT SELECT ON v_user_activity_metrics TO anon, authenticated;
GRANT SELECT ON v_compliance_violation_cumulative TO anon, authenticated;

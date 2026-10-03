-- Migration 0008: Analytics Star Schema

CREATE TABLE IF NOT EXISTS dim_document_types (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);

INSERT INTO dim_document_types (type_name, description) VALUES
('NDA', 'Non-Disclosure Agreement'),
('Employment Agreement', 'Employment Agreement'),
('Lease Agreement', 'Lease Agreement'),
('Franchise Agreement', 'Franchise Agreement'),
('SaaS Agreement', 'Software as a Service Agreement'),
('Commercial Agreement', 'Commercial Agreement'),
('Services Agreement', 'Services Agreement'),
('Unknown', 'Unknown Document Type')
ON CONFLICT (type_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS dim_clause_categories (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
);

INSERT INTO dim_clause_categories (category_name, description) VALUES
('Confidentiality & IP', 'Confidentiality and Intellectual Property'),
('Liability & Risk', 'Liability and Risk Allocation'),
('Dispute Resolution & Jurisdiction', 'Dispute Resolution and Jurisdiction'),
('Term & Termination', 'Term and Termination'),
('Restrictive Covenants', 'Restrictive Covenants'),
('Commercial Terms', 'Commercial Terms'),
('General & Boilerplate', 'General and Boilerplate Clauses')
ON CONFLICT (category_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS dim_risk_levels (
    id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) UNIQUE NOT NULL,
    severity_order INT NOT NULL,
    color_code VARCHAR(7) NOT NULL
);

INSERT INTO dim_risk_levels (level_name, severity_order, color_code) VALUES
('LOW', 1, '#22C55E'),
('MEDIUM', 2, '#F59E0B'),
('HIGH', 3, '#EF4444')
ON CONFLICT (level_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS dim_dates (
    date_key DATE PRIMARY KEY,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,
    week_of_year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

INSERT INTO dim_dates (date_key, year, quarter, month, day, day_of_week, week_of_year, is_weekend)
SELECT
    datum AS date_key,
    EXTRACT(YEAR FROM datum) AS year,
    EXTRACT(QUARTER FROM datum) AS quarter,
    EXTRACT(MONTH FROM datum) AS month,
    EXTRACT(DAY FROM datum) AS day,
    EXTRACT(ISODOW FROM datum) AS day_of_week,
    EXTRACT(WEEK FROM datum) AS week_of_year,
    CASE WHEN EXTRACT(ISODOW FROM datum) IN (6, 7) THEN true ELSE false END AS is_weekend
FROM generate_series('2024-01-01'::DATE, '2027-12-31'::DATE, '1 day'::interval) AS datum
ON CONFLICT (date_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS fact_document_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    document_type_id INT REFERENCES dim_document_types(id),
    analysis_date DATE REFERENCES dim_dates(date_key),
    risk_level_id INT REFERENCES dim_risk_levels(id),
    safety_score INT,
    clause_count INT DEFAULT 0,
    high_risk_clause_count INT DEFAULT 0,
    medium_risk_clause_count INT DEFAULT 0,
    low_risk_clause_count INT DEFAULT 0,
    compliance_violation_count INT DEFAULT 0,
    processing_duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fact_clause_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    category_id INT REFERENCES dim_clause_categories(id),
    risk_level_id INT REFERENCES dim_risk_levels(id),
    confidence_score FLOAT,
    analysis_date DATE REFERENCES dim_dates(date_key),
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_documents_scd2 (
    surrogate_key UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    filename VARCHAR(255),
    status VARCHAR(50),
    safety_score INT,
    risk_level VARCHAR(50),
    effective_from TIMESTAMP NOT NULL DEFAULT now(),
    effective_to TIMESTAMP DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT true
);

-- SCD2 Trigger Function
CREATE OR REPLACE FUNCTION trg_documents_scd2()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND (NEW.safety_score IS DISTINCT FROM OLD.safety_score OR NEW.risk_level IS DISTINCT FROM OLD.risk_level)) THEN
        -- Close current record
        UPDATE dim_documents_scd2
        SET is_current = false, effective_to = now()
        WHERE document_id = OLD.id AND is_current = true;
        
        -- Insert new record
        INSERT INTO dim_documents_scd2 (document_id, filename, status, safety_score, risk_level, effective_from, effective_to, is_current)
        VALUES (NEW.id, NEW.filename, NEW.status, NEW.safety_score, NEW.risk_level, now(), '9999-12-31', true);
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO dim_documents_scd2 (document_id, filename, status, safety_score, risk_level, effective_from, effective_to, is_current)
        VALUES (NEW.id, NEW.filename, NEW.status, NEW.safety_score, NEW.risk_level, now(), '9999-12-31', true);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_documents_scd2 ON documents;
CREATE TRIGGER trigger_documents_scd2
AFTER INSERT OR UPDATE OF safety_score, risk_level ON documents
FOR EACH ROW
EXECUTE FUNCTION trg_documents_scd2();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fact_document_analyses_doc_id ON fact_document_analyses(document_id);
CREATE INDEX IF NOT EXISTS idx_fact_document_analyses_user_id ON fact_document_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_fact_document_analyses_org_id ON fact_document_analyses(org_id);
CREATE INDEX IF NOT EXISTS idx_fact_document_analyses_date_key ON fact_document_analyses(analysis_date);

CREATE INDEX IF NOT EXISTS idx_fact_clause_risks_doc_id ON fact_clause_risks(document_id);
CREATE INDEX IF NOT EXISTS idx_fact_clause_risks_clause_id ON fact_clause_risks(clause_id);
CREATE INDEX IF NOT EXISTS idx_fact_clause_risks_date_key ON fact_clause_risks(analysis_date);

CREATE INDEX IF NOT EXISTS idx_dim_documents_scd2_doc_id ON dim_documents_scd2(document_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON dim_document_types TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON dim_clause_categories TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON dim_risk_levels TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON dim_dates TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fact_document_analyses TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fact_clause_risks TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON dim_documents_scd2 TO anon, authenticated;

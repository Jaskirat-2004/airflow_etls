-- MANUAL LEADS SENT BY THE CLIENT
-- always name the columns in the COPY so a new column in the client file cannot
-- land in source

CREATE TABLE leads_manual_staging (
    report_date              DATE,
    lead_id                  TEXT,
    lead_name                TEXT,
    phone                    TEXT,
    source                   TEXT NOT NULL DEFAULT 'manual'
);

CREATE TABLE leads_manual (
    report_date              DATE,
    lead_id                  TEXT,
    lead_name                TEXT,
    phone                    TEXT,
    source                   TEXT NOT NULL DEFAULT 'manual',
    updated_at               TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(report_date,phone)
);


-- UNIFIED LEADS VIEW TABLE UNION WITH CALL HISTORY
-- UNION ALL is deliberate: the leads fact groups by (report_date, phone) and
-- uses bool_or(source='prod') to derive 'both'

CREATE VIEW leads_unified AS
SELECT report_date, lead_id, lead_name, phone, source
FROM leads_manual

UNION ALL

SELECT DISTINCT
    report_date,
    lead_id::text      AS lead_id,
    lead_name          AS lead_label,
    phone,
    'prod'             AS source
FROM call_history
WHERE lead_name ILIKE 'prod%';

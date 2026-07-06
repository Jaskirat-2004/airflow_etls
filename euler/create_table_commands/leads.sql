
-- MANUA:L LEADS SENT BY THE CLIENT

CREATE TABLE leads_manual (
    report_date              DATE,
    lead_id                  TEXT,
    lead_name                TEXT,
    phone                    TEXT,
    source                   TEXT NOT NULL DEFAULT 'manual'
);


-- UNIFIED LEADS VIEW TABLE UNION WITH CALL HISTORY 

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

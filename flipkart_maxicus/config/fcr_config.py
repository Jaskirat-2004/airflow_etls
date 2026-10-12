# JS =============================================================================================================== JS
#                                        QUERIES FOR FCR REPORT FACT TABLE
# JS =============================================================================================================== JS
#  LAST_DATE : 2026-09-18

# JS ======================================= DDL ======================================= JS

FLIPKART_FACT_FCR_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS flipkart_maxicus.flipkart_fact_fcr_report
(
    report_date                Date,
    fcr_window_days            UInt8,           -- 1 or 7. ALWAYS filter on this
    tenant_name                String,
    entity_name                String,

    fc_session_id              String,
    fc_incident_id             String,
    fc_contact_ts              Nullable(DateTime),
    fc_contact_lag_days        Int16,
    fc_contact_rank            Int16,
    week_label                 String,

    fc_status                  String,          -- Pass / Fail
    fc_repeat_flag             String,          -- NOT the verdict

    fc_agent_id                String,          -- the LDAP, lowercased
    fc_cohort_name             String,
    fc_tenure_bucket           String,

    mp_emp_id                  String,          -- the Maxicus ID
    mp_agent_name              String,
    mp_designation             String,
    mp_team_leader_name        String,
    mp_manager_name            String,
    mp_status_internal         String,
    mp_production_date         Nullable(Date),  -- feeds aon_days / aon_bucket on the dataset
    mp_ojt_start_date          Nullable(Date),

    fc_journey_node            String,
    fc_jn_group                String,
    fc_ssi                     String,
    fc_ocr_classification      String,
    fc_business_unit           String,          -- blanks land as 'Not Classified'

    lead_partner_location      String,          -- where the repeat landed
    lead_agent_id              String,
    lead_lob                   String,

    total_interactions         UInt8,
    pass_count                 UInt8,
    fail_count                 UInt8,

    loaded_at                  DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, fcr_window_days, fc_agent_id, fc_session_id)

"""

# JS ======================================= FACT TABLE ======================================= JS

FLIPKART_FACT_FCR_REPORT_QUERY = """

WITH mp AS (
    -- ldap_id is unique 414/414 today and 667/667 in the pending reload, so no dedup is needed.
    -- Both date branches are required: the table holds 'DD-Mon-YY' now, the reload holds Excel serials.
    SELECT LOWER(TRIM(ldap_id))                  AS ldap_id,
           NULLIF(TRIM(maxicus_id), '-')         AS maxicus_id,
           employee_full_name,
           designation,
           NULLIF(TRIM(team_leader_name), '-')   AS team_leader_name,
           NULLIF(TRIM(manager_name), '-')       AS manager_name,
           NULLIF(TRIM(status_internal), '-')    AS status_internal,
           CASE WHEN production_date ~ '^[0-9.]+$' THEN DATE '1899-12-30' + FLOOR(production_date::numeric)::int
                WHEN NULLIF(TRIM(production_date), '-') IS NOT NULL THEN TO_DATE(production_date, 'DD-Mon-YY')
           END                                   AS production_date,
           CASE WHEN ojt_start_date ~ '^[0-9.]+$' THEN DATE '1899-12-30' + FLOOR(ojt_start_date::numeric)::int
                WHEN NULLIF(TRIM(ojt_start_date), '-') IS NOT NULL THEN TO_DATE(ojt_start_date, 'DD-Mon-YY')
           END                                   AS ojt_start_date
    FROM mapper_dim
    WHERE TRIM(COALESCE(ldap_id, '')) NOT IN ('', '-')
),

f AS (
    SELECT 1 AS fcr_window_days, report_date, session_id, incident_id, contact_date, contact_rank,
           status, repeat_flag, agent_id, sbr_primary_cohort, tenure_bucket,
           journey_node, jn_group, ssi, ocr_classification, analytic_business_unit,
           lead_partner_location, lead_agent_id, lead_lob
    FROM   fcr_dump_d1 WHERE report_date > DATE '{last_processed}'
    UNION ALL
    SELECT 7 AS fcr_window_days, report_date, session_id, incident_id, contact_date, contact_rank,
           status, repeat_flag, agent_id, sbr_primary_cohort, tenure_bucket,
           journey_node, jn_group, ssi, ocr_classification, analytic_business_unit,
           lead_partner_location, lead_agent_id, lead_lob
    FROM   fcr_dump_d7 WHERE report_date > DATE '{last_processed}'
)

SELECT
    f.report_date                                       AS report_date,
    f.fcr_window_days                                   AS fcr_window_days,
    'flipkart'                                          AS tenant_name,
    'maxicus'                                           AS entity_name,

    f.session_id                                        AS fc_session_id,
    COALESCE(f.incident_id, '')                         AS fc_incident_id,
    f.contact_date                                      AS fc_contact_ts,
    COALESCE((f.contact_date::date - f.report_date), 0) AS fc_contact_lag_days,
    COALESCE(f.contact_rank, 0)                         AS fc_contact_rank,
    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM f.report_date) / 7.0), 4)::int::text
                                                        AS week_label,

    COALESCE(TRIM(f.status), '')                        AS fc_status,
    COALESCE(TRIM(f.repeat_flag), '')                   AS fc_repeat_flag,

    LOWER(TRIM(COALESCE(f.agent_id, '')))               AS fc_agent_id,
    COALESCE(TRIM(f.sbr_primary_cohort), '')            AS fc_cohort_name,
    COALESCE(TRIM(f.tenure_bucket), '')                 AS fc_tenure_bucket,

    COALESCE(mp.maxicus_id, '')                         AS mp_emp_id,
    COALESCE(mp.employee_full_name, '')                 AS mp_agent_name,
    COALESCE(mp.designation, '')                        AS mp_designation,
    COALESCE(mp.team_leader_name, '')                   AS mp_team_leader_name,
    COALESCE(mp.manager_name, '')                       AS mp_manager_name,
    COALESCE(mp.status_internal, '')                    AS mp_status_internal,
    mp.production_date                                  AS mp_production_date,
    mp.ojt_start_date                                   AS mp_ojt_start_date,

    COALESCE(TRIM(f.journey_node), '')                  AS fc_journey_node,
    COALESCE(TRIM(f.jn_group), '')                      AS fc_jn_group,
    COALESCE(TRIM(f.ssi), '')                           AS fc_ssi,
    COALESCE(TRIM(f.ocr_classification), '')            AS fc_ocr_classification,
    COALESCE(NULLIF(TRIM(f.analytic_business_unit), ''), 'Not Classified')
                                                        AS fc_business_unit,

    COALESCE(TRIM(f.lead_partner_location), '')         AS lead_partner_location,
    COALESCE(TRIM(f.lead_agent_id), '')                 AS lead_agent_id,
    COALESCE(TRIM(f.lead_lob), '')                      AS lead_lob,

    -- LOWER(): Excel matched 'Pass' case-insensitively, Postgres does not.
    1                                                   AS total_interactions,
    (LOWER(TRIM(COALESCE(f.status, ''))) = 'pass')::int AS pass_count,
    (LOWER(TRIM(COALESCE(f.status, ''))) = 'fail')::int AS fail_count

FROM f
LEFT JOIN mp ON mp.ldap_id = LOWER(TRIM(f.agent_id))

"""

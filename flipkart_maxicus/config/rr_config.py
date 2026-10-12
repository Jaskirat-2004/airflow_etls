# JS =============================================================================================================== JS
#                                        QUERIES FOR RR REPORT FACT TABLE
# JS =============================================================================================================== JS
#  LAST_DATE : 2026-09-11
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

FLIPKART_FACT_RR_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS flipkart_maxicus.flipkart_fact_rr_report
(
    report_date              Date,
    tenant_name              String,
    entity_name              String,

    rr_incident_id           String,
    rr_response_date         Date,
    rr_agent_id              String,
    rr_response              String,
    rr_issue_type            String,
    rr_sub_issue_type        String,
    rr_sub_sub_issue_type    String,
    rr_cohort_name           String,
    rr_tenure_days           Nullable(Int32),

    mp_maxicus_id            String,
    mp_agent_name            String,
    mp_designation           String,
    mp_batch_no              String,
    mp_status_internal       String,
    mp_production_date       Nullable(Date),

    hc_reporting_to_name     String,
    hc_functional_rm_name    String,

    aon_days                 Nullable(Int32),
    aon_bucket               String,

    loaded_at                DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, rr_agent_id, rr_incident_id)
"""

# JS ======================================= FACT TABLE ======================================= JS

FLIPKART_FACT_RR_REPORT_QUERY = """

WITH mp AS (
    SELECT DISTINCT ON (ldap_id)
           ldap_id,
           NULLIF(maxicus_id, '-')          AS maxicus_id,
           employee_full_name,
           designation,
           NULLIF(batch_no, '-')            AS batch_no,
           status_internal,

           CASE WHEN production_date ~ '^[0-9.]+$'
                     THEN DATE '1899-12-30' + FLOOR(production_date::numeric)::int

                WHEN NULLIF(production_date, '-') IS NOT NULL
                     THEN TO_DATE(production_date, 'DD-Mon-YY')
           END                              AS production_date

    FROM mapper_dim
)

SELECT
    r.report_date                                       AS report_date,
    'flipkart'                                          AS tenant_name,
    'maxicus'                                           AS entity_name,

    r.incident_id                                       AS rr_incident_id,
    r.response_date                                     AS rr_response_date,
    LOWER(TRIM(r.agent_id))                             AS rr_agent_id,
    COALESCE(r.response, '')                            AS rr_response,
    COALESCE(r.issue_type, '')                          AS rr_issue_type,
    COALESCE(r.sub_issue_type, '')                      AS rr_sub_issue_type,
    COALESCE(r.sub_sub_issue_type, '')                  AS rr_sub_sub_issue_type,
    COALESCE(r.sbr_primary_cohort, '')                  AS rr_cohort_name,
    NULLIF(r.tenure_days, '')::numeric::int             AS rr_tenure_days,

    COALESCE(mp.maxicus_id, '')                         AS mp_maxicus_id,
    COALESCE(mp.employee_full_name, '')                 AS mp_agent_name,
    COALESCE(mp.designation, '')                        AS mp_designation,
    COALESCE(mp.batch_no, '')                           AS mp_batch_no,
    COALESCE(mp.status_internal, '')                    AS mp_status_internal,
    mp.production_date                                  AS mp_production_date,

    COALESCE(hc.reporting_to_name, '')                  AS hc_reporting_to_name,
    COALESCE(hc.functional_reporting_to_name, '')       AS hc_functional_rm_name,

    (r.report_date - mp.production_date)                AS aon_days,
    
    CASE WHEN mp.production_date IS NULL              THEN '<0 (OJT)'
         WHEN r.report_date <  mp.production_date     THEN '<0 (OJT)'
         WHEN r.report_date -  mp.production_date < 30 THEN '0-30'
         WHEN r.report_date -  mp.production_date < 60 THEN '30-60'
         WHEN r.report_date -  mp.production_date < 90 THEN '60-90'
         WHEN r.report_date -  mp.production_date < 180 THEN '90-180'
         ELSE '180+' END                                 AS aon_bucket

FROM rr_dump r
LEFT JOIN mp ON mp.ldap_id = LOWER(TRIM(r.agent_id))
LEFT JOIN head_count hc ON hc.report_date = r.report_date
                       AND hc.employee_id = mp.maxicus_id
WHERE r.report_date >  DATE '{last_processed}'
  AND r.report_date <= DATE '{high_water_mark}'
"""

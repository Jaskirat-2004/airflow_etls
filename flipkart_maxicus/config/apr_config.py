# JS =============================================================================================================== JS
#                                       QUERIES FOR APR REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

FLIPKART_FACT_APR_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS flipkart_maxicus.flipkart_fact_apr_report
(
    report_date                Date,
    tenant_name                String,
    entity_name                String,

    ap_login_id                String,
    ap_ldap_id                 String,
    ap_login_name              String,          -- Avaya free-text. AUDIT ONLY.
    mandays                    UInt8,           -- literal 1. SUM this, never COUNT(DISTINCT agent).

    -- agent attributes from the mapper, via avaya_id
    mp_emp_id                  String,          -- the Maxicus ID
    mp_agent_name              String,          -- THE display name
    mp_designation             String,          -- the agent-vs-support filter
    mp_batch_no                String,
    mp_cohort_name             String,
    mp_team_leader_name        String,
    mp_manager_name            String,

    mp_status_internal         String,          -- Training / Production / OJT, from the mapper
    mp_production_date         Nullable(Date),
    mp_ojt_start_date          Nullable(Date),

    -- HRMS reporting line from head_count, via emp_id (agents only, ~68% by design)
    hc_reporting_to_name       String,
    hc_functional_rm_name      String,

    -- ===== the Avaya block, complete. All additive, ALL SECONDS. =====

    ap_acd_calls               Int32,
    ap_acd_time_secs           Int32,
    ap_hold_time_secs          Int32,
    ap_acw_time_secs           Int32,
    ap_ring_time_secs          Int32,
    ap_avail_time_secs         Int32,
    ap_staffed_secs            Int32,
    ap_net_login_secs          Int32,           -- staffed - aux. THE Occupancy denominator.
    ap_trans_out               Int32,
    ap_conf                    Int32,
    ap_acd_calls_released      Int32,
    ap_extn_out_calls          Int32,

    -- AUX: these ten sum to ap_aux_secs (gate 2)
    ap_aux_secs                Int32,
    ap_aux_default_secs        Int32,
    ap_aux_tea_break_secs      Int32,
    ap_aux_floor_support_secs  Int32,
    ap_aux_lunch_secs          Int32,
    ap_aux_training_secs       Int32,
    ap_aux_feedback_secs       Int32,
    ap_aux_meeting_secs        Int32,
    ap_aux_system_issue_secs   Int32,
    ap_aux_callback_secs       Int32,
    ap_aux_logout_secs         Int32,

    ap_hold_ge_2min_flag       UInt8,           -- 1 iff DAILY hold >= 120 s. See note below.

    week_label                 String,
    loaded_at                  DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, ap_login_id)

"""

# JS ======================================= FACT TABLE ======================================= JS

FLIPKART_FACT_APR_REPORT_QUERY = """


WITH mp AS (

    SELECT DISTINCT ON (LOWER(TRIM(avaya_id)))
           LOWER(TRIM(avaya_id))                  AS avaya_id,
           NULLIF(TRIM(maxicus_id), '-')          AS maxicus_id,
           NULLIF(TRIM(ldap_id), '-')             AS ldap_id,
           employee_full_name,
           designation,
           NULLIF(TRIM(batch_no), '-')            AS batch_no,
           NULLIF(TRIM(sbr_primary_cohort), '-')  AS sbr_primary_cohort,
           NULLIF(TRIM(team_leader_name), '-')    AS team_leader_name,
           NULLIF(TRIM(manager_name), '-')        AS manager_name,
           NULLIF(TRIM(status_internal), '-')     AS status_internal,
           CASE WHEN production_date ~ '^[0-9.]+$'
                     THEN DATE '1899-12-30' + FLOOR(production_date::numeric)::int
                WHEN NULLIF(TRIM(production_date), '-') IS NOT NULL
                     THEN TO_DATE(production_date, 'DD-Mon-YY')
           END                                    AS production_date,
           CASE WHEN ojt_start_date ~ '^[0-9.]+$'
                     THEN DATE '1899-12-30' + FLOOR(ojt_start_date::numeric)::int
                WHEN NULLIF(TRIM(ojt_start_date), '-') IS NOT NULL
                     THEN TO_DATE(ojt_start_date, 'DD-Mon-YY')
           END                                    AS ojt_start_date
    FROM mapper_dim
    WHERE TRIM(COALESCE(avaya_id, '')) NOT IN ('', '-', '0')
    ORDER BY LOWER(TRIM(avaya_id)), (NULLIF(TRIM(maxicus_id), '-') IS NOT NULL) DESC
),

ap AS (
    SELECT *, LOWER(TRIM(login_id)) AS k
    FROM apr_dump
    WHERE report_date >  DATE '{last_processed}'
      AND report_date <= DATE '{high_water_mark}'
)

SELECT
    ap.report_date                                      AS report_date,
    'flipkart'                                          AS tenant_name,
    'maxicus'                                           AS entity_name,

    ap.k                                                AS ap_login_id,
    COALESCE(mp.ldap_id, '')                            AS ap_ldap_id,
    COALESCE(ap.login_name, '')                         AS ap_login_name,
    1                                                   AS mandays,

    COALESCE(mp.maxicus_id, '')                         AS mp_emp_id,
    COALESCE(mp.employee_full_name, '')                 AS mp_agent_name,
    COALESCE(mp.designation, '')                        AS mp_designation,
    COALESCE(mp.batch_no, '')                           AS mp_batch_no,
    COALESCE(mp.sbr_primary_cohort, '')                 AS mp_cohort_name,
    COALESCE(mp.team_leader_name, '')                   AS mp_team_leader_name,
    COALESCE(mp.manager_name, '')                       AS mp_manager_name,

    COALESCE(mp.status_internal, '')                    AS mp_status_internal,
    mp.production_date                                  AS mp_production_date,
    mp.ojt_start_date                                   AS mp_ojt_start_date,

    COALESCE(hc.reporting_to_name, '')                  AS hc_reporting_to_name,
    COALESCE(hc.functional_reporting_to_name, '')       AS hc_functional_rm_name,

    ap.acd_calls                                        AS ap_acd_calls,
    ap.acd_time_secs                                    AS ap_acd_time_secs,
    ap.hold_time_secs                                   AS ap_hold_time_secs,
    ap.acw_time_secs                                    AS ap_acw_time_secs,
    ap.ring_time_secs                                   AS ap_ring_time_secs,
    ap.avail_time_secs                                  AS ap_avail_time_secs,
    ap.staffed_secs                                     AS ap_staffed_secs,
    (ap.staffed_secs - ap.aux_secs)                     AS ap_net_login_secs,
    ap.trans_out                                        AS ap_trans_out,
    ap.conf                                             AS ap_conf,
    ap.acd_calls_released                               AS ap_acd_calls_released,
    ap.extn_out_calls                                   AS ap_extn_out_calls,

    ap.aux_secs                                         AS ap_aux_secs,
    ap.aux_default_secs                                 AS ap_aux_default_secs,
    ap.aux_tea_break_secs                               AS ap_aux_tea_break_secs,
    ap.aux_floor_support_secs                           AS ap_aux_floor_support_secs,
    ap.aux_lunch_secs                                   AS ap_aux_lunch_secs,
    ap.aux_training_secs                                AS ap_aux_training_secs,
    ap.aux_feedback_secs                                AS ap_aux_feedback_secs,
    ap.aux_meeting_secs                                 AS ap_aux_meeting_secs,
    ap.aux_system_issue_secs                            AS ap_aux_system_issue_secs,
    ap.aux_callback_secs                                AS ap_aux_callback_secs,
    ap.aux_logout_secs                                  AS ap_aux_logout_secs,

    (ap.hold_time_secs >= 120)::int                     AS ap_hold_ge_2min_flag,

    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM ap.report_date) / 7.0), 4)::int::text
                                                        AS week_label

FROM ap
LEFT JOIN mp ON mp.avaya_id = ap.k

LEFT JOIN head_count hc ON hc.report_date = ap.report_date
                       AND TRIM(hc.employee_id) = mp.maxicus_id

"""

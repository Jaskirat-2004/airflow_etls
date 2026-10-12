# JS =============================================================================================================== JS
#                                       QUERIES FOR AGENT HYGIENE REPORT FACT TABLE
# JS =============================================================================================================== JS
#  LAST_DATE : 2026-09-17

# JS ======================================= DDL ======================================= JS

FLIPKART_FACT_AGENT_HYGIENE_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS flipkart_maxicus.flipkart_fact_agent_hygiene_report
(
    report_date              Date,
    tenant_name              String,
    entity_name              String,

    -- identity of the ROW
    ec_anslogin              String,          -- Avaya extension (the agent)
    ec_cohort                String,          -- from dispsplit: the queue the calls came on
    ec_dispsplit             String,          -- the raw skill code, kept for audit

    -- agent attributes, from the mapper via avaya_id
    mp_emp_id                String,
    mp_ldap_id               String,
    mp_agent_name            String,
    mp_batch_no              String,
    mp_designation           String,
    mp_team_leader_name      String,
    mp_agent_cohort          String,          -- the agent's HOME cohort - for contrast only
    mp_production_date       Nullable(Date),
    aon_days                 Nullable(Int32),

    hc_reporting_to_name     String,
    hc_functional_rm_name    String,

    -- counts, all additive
    total_calls              UInt32,
    answered_calls           UInt32,
    short_calls              UInt32,
    agent_disconnections     UInt32,
    held_calls               UInt32,
    hold_gt_2min_calls       UInt32,
    transferred_calls        UInt32,          -- not published by the client; free win
    holdabn_calls            UInt32,          -- not published by the client; free win

    -- seconds, all additive
    hold_secs                UInt64,
    tht_secs                 UInt64,
    talk_secs                UInt64,
    acw_secs                 UInt64,
    ring_secs                UInt64,
    queue_secs               UInt64,

    week_label               String,
    loaded_at                DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, ec_anslogin, ec_cohort)

"""

# JS ======================================= FACT TABLE ======================================= JS

FLIPKART_FACT_AGENT_HYGIENE_REPORT_QUERY = """

WITH agg AS (
    SELECT
        d.report_date,
        LOWER(TRIM(COALESCE(d.anslogin, '')))                     AS anslogin,
        d.dispsplit,

        COUNT(*)::int                                             AS total_calls,
        SUM((d.disposition = '2')::int)::int                      AS answered_calls,
        SUM((d.disposition = '2' AND d.talktime <> 0 AND d.talktime <= 5)::int)::int
                                                                  AS short_calls,
        SUM(CASE WHEN d.conference = 1 OR d.transferred = 1 THEN 0
                 ELSE COALESCE(d.agt_released, 0) END)::int       AS agent_disconnections,
        SUM((d.disposition = '2' AND d.ansholdtime > 0)::int)::int
                                                                  AS held_calls,
        SUM((d.disposition = '2' AND d.ansholdtime >= 120)::int)::int
                                                                  AS hold_gt_2min_calls,
        SUM((d.disposition = '2' AND d.transferred = 1)::int)::int AS transferred_calls,
        SUM((d.disposition = '2' AND d.holdabn = 1)::int)::int     AS holdabn_calls,

        SUM(COALESCE(d.ansholdtime, 0))::bigint                   AS hold_secs,
        SUM(COALESCE(d.acwtime, 0) + COALESCE(d.ansholdtime, 0)
            + COALESCE(d.talktime, 0))::bigint                    AS tht_secs,
        SUM(COALESCE(d.talktime, 0))::bigint                      AS talk_secs,
        SUM(COALESCE(d.acwtime, 0))::bigint                       AS acw_secs,
        SUM(COALESCE(d.ringtime, 0))::bigint                      AS ring_secs,
        SUM(COALESCE(d.queuetime, 0))::bigint                     AS queue_secs

    FROM echi_dump d

    WHERE d.report_date >  DATE '{last_processed}'
      AND d.report_date <= DATE '{high_water_mark}'

    GROUP BY 1, 2, 3
),

mp AS (
    SELECT DISTINCT ON (avaya_id)
           LOWER(TRIM(avaya_id))            AS avaya_id,
           NULLIF(maxicus_id, '-')          AS maxicus_id,
           ldap_id,
           employee_full_name,
           NULLIF(batch_no, '-')            AS batch_no,
           designation,
           NULLIF(team_leader_name, '-')    AS team_leader_name,
           NULLIF(sbr_primary_cohort, '-')  AS sbr_primary_cohort,
           CASE WHEN production_date ~ '^[0-9.]+$'
                     THEN DATE '1899-12-30' + FLOOR(production_date::numeric)::int
                WHEN NULLIF(production_date, '-') IS NOT NULL
                     THEN TO_DATE(production_date, 'DD-Mon-YY')
           END                              AS production_date
           
    FROM mapper_dim
    WHERE TRIM(COALESCE(avaya_id, '')) NOT IN ('', '-', '0')
    ORDER BY avaya_id, (maxicus_id IS DISTINCT FROM '-') DESC
)

SELECT
    a.report_date                                       AS report_date,
    'flipkart'                                          AS tenant_name,
    'maxicus'                                           AS entity_name,

    a.anslogin                                          AS ec_anslogin,
    CASE a.dispsplit WHEN '1738' THEN 'Catchall RE IB'
                     WHEN '1741' THEN 'Return RE IB'
                     ELSE 'Unmapped' END                 AS ec_cohort,
    a.dispsplit                                         AS ec_dispsplit,

    COALESCE(mp.maxicus_id, '')                         AS mp_emp_id,
    COALESCE(mp.ldap_id, '')                            AS mp_ldap_id,
    COALESCE(mp.employee_full_name, '')                 AS mp_agent_name,
    COALESCE(mp.batch_no, '')                           AS mp_batch_no,
    COALESCE(mp.designation, '')                        AS mp_designation,
    COALESCE(mp.team_leader_name, '')                   AS mp_team_leader_name,
    COALESCE(mp.sbr_primary_cohort, '')                 AS mp_agent_cohort,
    mp.production_date                                  AS mp_production_date,
    (a.report_date - mp.production_date)                AS aon_days,

    COALESCE(hc.reporting_to_name, '')                  AS hc_reporting_to_name,
    COALESCE(hc.functional_reporting_to_name, '')       AS hc_functional_rm_name,

    a.total_calls, a.answered_calls, a.short_calls, a.agent_disconnections,
    a.held_calls, a.hold_gt_2min_calls, a.transferred_calls, a.holdabn_calls,
    a.hold_secs, a.tht_secs, a.talk_secs, a.acw_secs, a.ring_secs, a.queue_secs,

    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM a.report_date) / 7.0), 4)::int::text
                                                        AS week_label
FROM agg a
LEFT JOIN mp ON mp.avaya_id = a.anslogin
LEFT JOIN head_count hc ON hc.report_date = a.report_date
                       AND hc.employee_id = mp.maxicus_id

"""








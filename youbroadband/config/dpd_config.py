# JS =============================================================================================================== JS
#                                       QUERIES FOR DPD REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

YOUBROADBAND_FACT_DPD_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS youbroadband.youbroadband_fact_dpd_report
(
    report_date        Date,
    week               String,
    tenant_name        String,
    entity_name        String,
    process            Nullable(String),
    campaign           Nullable(String),

    ivr_offered        Int32,
    forecast_calls     Int32,

    acd_offered        Int32,
    acd_answered       Int32,
    acd_abandoned      Int32,
    acd_ans_in_20      Int32,
    acd_aban_in_20     Int32,
    acd_hold_secs      Int32,

    ap_ready_secs      Int32,
    ap_talk_secs       Int32,
    ap_acw_secs        Int32,
    ap_idle_secs       Int32,

    tht_secs           Int32,

    cd_calls           Int32,
    cd_ans_in_90       Int32,

    sl_target_pct      Float32,
    al_target_pct      Float32,
    aban_target_pct    Float32,

    loaded_at          DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date)

"""

# JS ======================================= FACT TABLE ======================================= JS

YOUBROADBAND_FACT_DPD_REPORT_QUERY = """

WITH acd AS (
    SELECT
        report_date,
        MAX(process_name)                                                       AS process_name,
        MAX(campaign_name)                                                      AS campaign_name,
        SUM(total_received_calls)                                               AS offered,
        SUM(total_connected_calls)                                              AS answered,
        SUM(total_abandoned_calls_at_acd)                                       AS abandoned,
        SUM(total_connected_in_target)                                          AS ans_in_20,
        SUM(total_abandoned_before_target)                                      AS aban_in_20,
        SUM(EXTRACT(EPOCH FROM NULLIF(total_hold_duration,'')::interval)::int)  AS hold_secs
    FROM acd_call_interval_summary
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1
),

ap AS (
    SELECT
        report_date,
        SUM(EXTRACT(EPOCH FROM NULLIF(total_ready_duration,'')::interval)::int)            AS ready_secs,
        SUM(EXTRACT(EPOCH FROM NULLIF(total_talk_time_in_interval,'')::interval)::int)     AS talk_secs,
        SUM(EXTRACT(EPOCH FROM NULLIF(total_acw_duration_in_interval,'')::interval)::int)  AS acw_secs,
        SUM(EXTRACT(EPOCH FROM NULLIF(total_idle_time,'')::interval)::int)                 AS idle_secs
    FROM agent_productivity_interval_summary
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
      AND campaign_name = 'Youbroadband'
    GROUP BY 1
),

ivr AS (
    SELECT report_date, COUNT(*) AS ivr_offered
    FROM ivr_footprint
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1
),

cd AS (
    SELECT
        report_date,
        COUNT(*)                                                                              AS cd_calls,
        COUNT(*) FILTER (WHERE EXTRACT(EPOCH FROM NULLIF(total_wait_time,'')::interval) <= 90) AS ans_in_90
    FROM acd_call_details
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1
)
SELECT
    a.report_date,
    -- Week-N = ceil(day/7) capped at 4. Verified: days 1-7 sum to the client's Week-1 on both
    -- IVR offered (13,823) and Total Offered (8,340).
    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM a.report_date) / 7.0)::int, 4)::text  AS week,
    'youbroadband'                                    AS tenant_name,
    'maxicus'                                         AS entity_name,
    a.process_name                                    AS process,
    a.campaign_name                                   AS campaign,

    COALESCE(v.ivr_offered,0)                         AS ivr_offered,
    COALESCE(f.forecast,0)                            AS forecast_calls,

    COALESCE(a.offered,0)                             AS acd_offered,
    COALESCE(a.answered,0)                            AS acd_answered,
    COALESCE(a.abandoned,0)                           AS acd_abandoned,
    COALESCE(a.ans_in_20,0)                           AS acd_ans_in_20,
    COALESCE(a.aban_in_20,0)                          AS acd_aban_in_20,
    COALESCE(a.hold_secs,0)                           AS acd_hold_secs,

    COALESCE(p.ready_secs,0)                          AS ap_ready_secs,
    COALESCE(p.talk_secs,0)                           AS ap_talk_secs,
    COALESCE(p.acw_secs,0)                            AS ap_acw_secs,
    COALESCE(p.idle_secs,0)                           AS ap_idle_secs,

    -- THT = APSI talk + ACD hold + APSI acw. See rule 3 in the header.
    (COALESCE(p.talk_secs,0) + COALESCE(a.hold_secs,0) + COALESCE(p.acw_secs,0))  AS tht_secs,

    COALESCE(c.cd_calls,0)                            AS cd_calls,
    COALESCE(c.ans_in_90,0)                           AS cd_ans_in_90,

    -- SLA contract, client Index sheet. Use MAX() in charts, never SUM().
    80.0                                              AS sl_target_pct,
    97.0                                              AS al_target_pct,
    3.0                                               AS aban_target_pct

FROM acd a
LEFT JOIN ap  p ON p.report_date = a.report_date
LEFT JOIN ivr v ON v.report_date = a.report_date
LEFT JOIN cd  c ON c.report_date = a.report_date
LEFT JOIN forecast f ON f.report_date = a.report_date
ORDER BY a.report_date

"""

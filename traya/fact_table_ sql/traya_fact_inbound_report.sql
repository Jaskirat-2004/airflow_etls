
-- ---------- ACD per agent x 30-min interval ----------
WITH acd AS (
    SELECT
        call_time::date                                                                               AS report_date,
        date_trunc('hour', call_time) + floor(extract(minute from call_time)/30)*interval '30 minute' AS interval_start,
        COALESCE(NULLIF(lower(trim(user_id)),''), '(queue_abandoned)')                                AS agent_email,

        count(*)                                                                                      AS acd_offered,
        count(*) FILTER (WHERE upper(answered_hungup)='ANSWERED')                                     AS acd_answered,
        count(*) FILTER (WHERE upper(answered_hungup)='HUNGUP')                                       AS acd_abandoned,
        count(*) FILTER (WHERE upper(answered_hungup)='HUNGUP'
                           AND extract(epoch from wait_time::interval) <= 3)                          AS acd_abandoned_3s,
        count(*) FILTER (WHERE upper(answered_hungup)='ANSWERED'
                           AND extract(epoch from user_talk_time::interval) < 60)                     AS acd_short_60,
        count(*) FILTER (WHERE upper(answered_hungup)='ANSWERED'
                           AND extract(epoch from user_talk_time::interval) < 3)                      AS acd_short_lt3,
        count(*) FILTER (WHERE upper(answered_hungup)='ANSWERED'
                           AND extract(epoch from user_talk_time::interval) >= 5
                           AND extract(epoch from user_talk_time::interval) <= 15)                    AS acd_short_5_15,
        count(*) FILTER (WHERE upper(answered_hungup)='ANSWERED'
                           AND extract(epoch from user_talk_time::interval) >= 16
                           AND extract(epoch from user_talk_time::interval) <= 30)                    AS acd_short_16_30,

        COALESCE(sum(extract(epoch from user_talk_time::interval)),0)::bigint                         AS acd_talk_secs,
        COALESCE(sum(extract(epoch from customer_hold::interval)),0)::bigint                          AS acd_hold_secs,
        COALESCE(sum(extract(epoch from acw_duration::interval)),0)::bigint                           AS acd_acw_secs,
        COALESCE(sum(extract(epoch from user_talk_time::interval)
                   + extract(epoch from customer_hold::interval)
                   + extract(epoch from acw_duration::interval)),0)::bigint                           AS acd_tht_secs,
        COALESCE(sum(extract(epoch from wait_time::interval)),0)::bigint                              AS acd_wait_secs

    FROM acd_call_details
    WHERE campaign_name = 'Inbound_Campaign'      -- consider: AND call_type='inbound.call.dial' (guard for full multi-campaign dumps)
    GROUP BY 1,2,3
),

-- ---------- interval summary (inbound campaign) per agent x 30-min ----------
ap AS (
    SELECT
        report_date,
        interval_start,
        lower(trim(user_id))                                                                          AS agent_email,

        COALESCE(sum(extract(epoch from total_staffed_duration::interval)),0)::bigint                 AS ap_staffed_secs,
        COALESCE(sum(extract(epoch from total_ready_duration::interval)),0)::bigint                   AS ap_ready_secs,
        COALESCE(sum(extract(epoch from total_break_duration::interval)),0)::bigint                   AS ap_break_secs,
        COALESCE(sum(extract(epoch from total_idle_time::interval)),0)::bigint                        AS ap_idle_secs,
        COALESCE(sum(extract(epoch from total_talk_time_in_interval::interval)),0)::bigint            AS ap_talk_secs,
        COALESCE(sum(extract(epoch from total_acw_duration_in_interval::interval)),0)::bigint         AS ap_acw_secs,
        COALESCE(sum(extract(epoch from total_customer_hold_duration::interval)),0)::bigint           AS ap_hold_secs,
        COALESCE(sum(extract(epoch from total_ring_time::interval)),0)::bigint                        AS ap_ring_secs,
        COALESCE(sum(connected_inbound),0)::int                                                       AS ap_connected_inbound,
        COALESCE(sum(inbound_received),0)::int                                                        AS ap_inbound_received,
        count(*)::int                                                                                 AS ap_intervals

        -- LOGIN COUNT
        COALESCE(sum(extract(epoch from total_ready_duration::interval)),0)/28800.0   AS ap_login_count

    FROM agent_productivity_interval_summary
    WHERE campaign_name = 'Inbound_Campaign'
    GROUP BY 1,2,3
),

-- ---------- roster dims (APR-style), one row per (date, agent) ----------
mt AS (
    SELECT DISTINCT ON (report_date, lower(trim(official_email)))
        report_date,
        lower(trim(official_email))   AS agent_email,

        emp_id                        AS mt_emp_id,
        emp_name                      AS mt_emp_name,
        designation                   AS mt_designation,
        group_name                    AS mt_group_name,
        sub_group                     AS mt_sub_group,  
        line_of_business              AS mt_lob,
        team_leader                   AS mt_team_leader,
        operations_manager            AS mt_operations_manager,
        tenure                        AS mt_tenure,

        CASE
            WHEN tenure ~ '^[0-9]+$' AND tenure::int <= 30              THEN '0-30'
            WHEN tenure ~ '^[0-9]+$' AND tenure::int BETWEEN 31 AND 60  THEN '31-60'
            WHEN tenure ~ '^[0-9]+$' AND tenure::int > 60               THEN '>60'
            ELSE 'Unknown'
        END                           AS mt_tenure_bucket,   -- computed on the tenure column

        date_of_joining               AS mt_doj,
        batch_number                  AS mt_batch,
        versant_score                 AS mt_versant,
        gender                        AS mt_gender,
        education_level               AS mt_education,
        fresher_experience            AS mt_fresher_exp,
        active_status                 AS mt_active_status,
        
        CASE
            WHEN group_name = 'Training' THEN 'Training'
            WHEN group_name = 'OJT'      THEN 'OJT'
            ELSE 'Live'
        END                           AS mt_status

    FROM master_tracker
    WHERE official_email IS NOT NULL AND official_email <> '' AND active_status = 'Active'
    ORDER BY report_date, lower(trim(official_email)), emp_id
)

-- ---------- final fact ----------
SELECT
    COALESCE(acd.report_date, ap.report_date)                                                        AS report_date,

    'Week-' || (
        FLOOR(
            (EXTRACT(DAY FROM COALESCE(acd.report_date, ap.report_date))
           + EXTRACT(ISODOW FROM date_trunc('month', COALESCE(acd.report_date, ap.report_date))) - 2) / 7
        ) + 1)::int::text                                                                            AS week,

    COALESCE(acd.agent_email, ap.agent_email)                                                        AS agent_email,

    'traya'                                                                                          AS tenant_name,
    'maxicus'                                                                                        AS entity_name,

    COALESCE(acd.interval_start, ap.interval_start)                                                  AS interval_start,

    -- master tracker
    mt.mt_emp_id,
    mt.mt_emp_name,
    mt.mt_designation,
    mt.mt_group_name,
    mt.mt_sub_group,
    mt.mt_lob,
    mt.mt_team_leader,
    mt.mt_operations_manager,
    mt.mt_tenure,
    mt.mt_tenure_bucket,
    mt.mt_doj,
    mt.mt_batch,
    mt.mt_versant,
    mt.mt_gender,
    mt.mt_education,
    mt.mt_fresher_exp,
    mt.mt_active_status,
    mt.mt_status,

    -- ACD per-call measures
    COALESCE(acd.acd_offered,0)        AS acd_offered,
    COALESCE(acd.acd_answered,0)       AS acd_answered,
    COALESCE(acd.acd_abandoned,0)      AS acd_abandoned,
    COALESCE(acd.acd_abandoned_3s,0)   AS acd_abandoned_3s,
    COALESCE(acd.acd_short_60,0)       AS acd_short_60,
    COALESCE(acd.acd_short_lt3,0)      AS acd_short_lt3,
    COALESCE(acd.acd_short_5_15,0)     AS acd_short_5_15,
    COALESCE(acd.acd_short_16_30,0)    AS acd_short_16_30,
    COALESCE(acd.acd_talk_secs,0)      AS acd_talk_secs,
    COALESCE(acd.acd_hold_secs,0)      AS acd_hold_secs,
    COALESCE(acd.acd_acw_secs,0)       AS acd_acw_secs,
    COALESCE(acd.acd_tht_secs,0)       AS acd_tht_secs,
    COALESCE(acd.acd_wait_secs,0)      AS acd_wait_secs,

    -- LOGIN COUNT
    COALESCE(ap.ap_login_count,0)      AS ap_login_count,

    -- interval-summary (agent time-state) measures
    COALESCE(ap.ap_staffed_secs,0)        AS ap_staffed_secs,
    COALESCE(ap.ap_ready_secs,0)          AS ap_ready_secs,
    COALESCE(ap.ap_break_secs,0)          AS ap_break_secs,
    COALESCE(ap.ap_idle_secs,0)           AS ap_idle_secs,
    COALESCE(ap.ap_talk_secs,0)           AS ap_talk_secs,
    COALESCE(ap.ap_acw_secs,0)            AS ap_acw_secs,
    COALESCE(ap.ap_hold_secs,0)           AS ap_hold_secs,
    COALESCE(ap.ap_ring_secs,0)           AS ap_ring_secs,
    COALESCE(ap.ap_connected_inbound,0)   AS ap_connected_inbound,
    COALESCE(ap.ap_inbound_received,0)    AS ap_inbound_received,
    COALESCE(ap.ap_intervals,0)           AS ap_intervals

FROM acd
FULL OUTER JOIN ap USING (report_date, interval_start, agent_email)
LEFT JOIN mt
    ON  mt.report_date = COALESCE(acd.report_date, ap.report_date)
    AND mt.agent_email = COALESCE(acd.agent_email, ap.agent_email)

WHERE COALESCE(acd.report_date, ap.report_date) > '{last_processed}'
    AND COALESCE(acd.report_date, ap.report_date) <= '{high_water_mark}'
    
-- ============================================================================
-- ClickHouse DDL  
-- ============================================================================

CREATE TABLE IF NOT EXISTS traya.traya_fact_inbound_report
(
    report_date              Date,
    week                     String,
    agent_email              String,
    tenant_name              String,
    entity_name              String,
    interval_start           DateTime,

    -- roster dims
    mt_emp_id                Nullable(String),
    mt_emp_name              Nullable(String),
    mt_designation           Nullable(String),
    mt_group_name            Nullable(String),
    mt_sub_group             Nullable(String),
    mt_lob                   Nullable(String),
    mt_team_leader           Nullable(String),
    mt_operations_manager    Nullable(String),
    mt_tenure                Nullable(String),
    mt_tenure_bucket         Nullable(String),
    mt_doj                   Nullable(String),
    mt_batch                 Nullable(String),
    mt_versant               Nullable(String),
    mt_gender                Nullable(String),
    mt_education             Nullable(String),
    mt_fresher_exp           Nullable(String),
    mt_active_status         Nullable(String),
    mt_status                Nullable(String),

    -- ACD per-call measures
    acd_offered              Int32,
    acd_answered             Int32,
    acd_abandoned            Int32,
    acd_abandoned_3s         Int32,
    acd_short_60             Int32,
    acd_short_lt3            Int32,
    acd_short_5_15           Int32,
    acd_short_16_30          Int32,
    acd_talk_secs            Int64,
    acd_hold_secs            Int64,
    acd_acw_secs             Int64,
    acd_tht_secs             Int64,
    acd_wait_secs            Int64,

    -- in DDL (last ap column):
    ap_login_count           Float64,

    -- interval-summary measures
    ap_staffed_secs          Int64,
    ap_ready_secs            Int64,
    ap_break_secs            Int64,
    ap_idle_secs             Int64,
    ap_talk_secs             Int64,
    ap_acw_secs              Int64,
    ap_hold_secs             Int64,
    ap_ring_secs             Int64,
    ap_connected_inbound     Int32,
    ap_inbound_received      Int32,
    ap_intervals             Int32
)
ENGINE = MergeTree()
ORDER BY (report_date, interval_start, agent_email);

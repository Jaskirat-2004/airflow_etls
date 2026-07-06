
CREATE TABLE IF NOT EXISTS eulermotors.euler_fact_apr_report
(
    report_date                 Date,
    agent_email                 String,
    campaign_name               String,
    location                    String,
    week                        String,
    tenant_name                 String,
    entity_name                 String,

    -- APR raw (productivity)  [Nullable: a ch-only agent-day has no productivity row]
    ap_intervals                Nullable(Int32),
    ap_staffed_secs             Nullable(Int64),
    ap_ready_secs               Nullable(Int64),
    ap_break_secs               Nullable(Int64),
    ap_idle_secs                Nullable(Int64),
    ap_service_secs             Nullable(Int64),
    ap_talk_secs                Nullable(Int64),
    ap_acw_secs                 Nullable(Int64),
    ap_hold_secs                Nullable(Int64),
    ap_ring_secs                Nullable(Int64),
    ap_wrapped_calls            Nullable(Int32),
    ap_auto_dials               Nullable(Int32),
    ap_auto_preview_dials       Nullable(Int32),
    ap_inbound_received         Nullable(Int32),
    ap_manual_dials             Nullable(Int32),
    ap_manual_preview_dials     Nullable(Int32),
    ap_callbacks_received       Nullable(Int32),
    ap_transfers_received       Nullable(Int32),
    ap_connected_auto           Nullable(Int32),
    ap_connected_inbound        Nullable(Int32),
    ap_connected_manual         Nullable(Int32),
    ap_connected_callbacks      Nullable(Int32),
    ap_connected_manual_preview Nullable(Int32),
    ap_connected_auto_preview   Nullable(Int32),
    ap_click_to_calls           Nullable(Int32),
    ap_connected_click_to_calls Nullable(Int32),
    ap_connected_transfers      Nullable(Int32),

    -- derived
    ap_total_offered            Nullable(Int64),
    ap_total_answered           Nullable(Int64),
    ap_tht                      Nullable(Int64),
    ap_capped_ready_secs        Float64,

    -- call_history pivots (COALESCEd → non-Nullable)
    ch_calls                    Int32,
    ch_inbound_calls            Int32,
    ch_outbound_calls           Int32,
    ch_connected                Int32,
    ch_not_connected            Int32,
    ch_unique_dialled           Int32,
    ch_unique_connected         Int32,
    ch_first_attempt            Int32,
    ch_first_attempt_connected  Int32,
    ch_successful_connect       Int32,
    ch_interested               Int32,
    ch_tagged                   Int32,
    ch_voicemail                Int32,
    ch_answered_hold_calls      Int32,
    ch_short_calls              Int32,
    ch_talk_secs                Int64,
    ch_cust_talk_secs           Int64,
    ch_acw_secs                 Int64,
    ch_hold_secs                Int64,
    ch_ivr_secs                 Int64,

    -- login share + allocated SQL (fractional)
    login_count                 Nullable(Float64),
    sql_allocated               Float64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, campaign_name, agent_email)



-- ==============================================================================
-- ==============================================================================
-- ==============================================================================
-- ==============================================================================

-- agent_productivity_interval_summary  (1 row already per date×campaign×agent)
WITH ap AS (
    SELECT
        report_date                                                                                            AS report_date,
        lower(trim(user_id))                                                                                   AS agent_email,
        campaign_name                                                                                          AS campaign_name,

        COUNT(*)                                                                                               AS ap_intervals,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_staffed_duration),'')::interval),0))::bigint         AS ap_staffed_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_ready_duration),'')::interval),0))::bigint           AS ap_ready_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_break_duration),'')::interval),0))::bigint           AS ap_break_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_idle_time),'')::interval),0))::bigint                AS ap_idle_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_service_time),'')::interval),0))::bigint             AS ap_service_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_talk_time_in_interval),'')::interval),0))::bigint    AS ap_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_acw_duration_in_interval),'')::interval),0))::bigint AS ap_acw_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_customer_hold_duration),'')::interval),0))::bigint   AS ap_hold_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_ring_time),'')::interval),0))::bigint                AS ap_ring_secs,

        SUM(auto_dials)                       AS ap_auto_dials,
        SUM(auto_preview_dials)               AS ap_auto_preview_dials,
        SUM(inbound_received)                 AS ap_inbound_received,
        SUM(manual_dials)                     AS ap_manual_dials,
        SUM(manual_preview_dials)             AS ap_manual_preview_dials,
        SUM(callbacks_received)               AS ap_callbacks_received,
        SUM(transfers_received)               AS ap_transfers_received,
        SUM(total_wrapped_calls)              AS ap_wrapped_calls,

        SUM(connected_auto_dials)             AS ap_connected_auto,
        SUM(connected_inbound)                AS ap_connected_inbound,
        SUM(connected_manual_dials)           AS ap_connected_manual,
        SUM(connected_callbacks)              AS ap_connected_callbacks,
        SUM(connected_manual_preview_dials)   AS ap_connected_manual_preview,
        SUM(connected_auto_preview_dials)     AS ap_connected_auto_preview,
        SUM(click_to_calls)                   AS ap_click_to_calls,
        SUM(connected_click_to_calls)         AS ap_connected_click_to_calls,
        SUM(connected_transfers)              AS ap_connected_transfers

    FROM agent_productivity_interval_summary
    WHERE user_id IS NOT NULL AND trim(user_id) <> ''
    GROUP BY 1,2,3
),

-- call_history per-call base (for flag-then-sum unique)
ch_base AS (
    SELECT
        call_time::date              AS report_date,
        lower(trim(user_id))         AS agent_email,
        campaign_name                AS campaign_name,

        phone, 
        system_disposition, 
        call_type, 
        disposition_code, 
        disposition_class, 
        attempt_number,
        user_talk_time, 
        customer_talk_time, 
        acw_duration, 
        customer_hold_duration, 
        ivr_time,

        EXTRACT(EPOCH FROM NULLIF(trim(user_talk_time),'')::interval)                AS talk_sec,

        row_number() OVER (PARTITION BY call_time::date, campaign_name, lower(trim(user_id)), phone
                           ORDER BY call_time)                                       AS rn_u,

        row_number() OVER (PARTITION BY call_time::date, campaign_name, lower(trim(user_id)), phone,
                                        (system_disposition='CONNECTED')
                           ORDER BY call_time)                                       AS rn_uc

    FROM call_history
    WHERE user_id IS NOT NULL AND trim(user_id) <> ''
),

ch AS (
    SELECT
        report_date, 
        agent_email, 
        campaign_name,

        COUNT(*)                                                                    AS ch_calls,
        COUNT(*) FILTER (WHERE call_type LIKE 'inbound%')                           AS ch_inbound_calls,
        COUNT(*) FILTER (WHERE call_type LIKE 'outbound%')                          AS ch_outbound_calls,
        COUNT(*) FILTER (WHERE system_disposition='CONNECTED')                      AS ch_connected,
        COUNT(*) FILTER (WHERE system_disposition<>'CONNECTED')                     AS ch_not_connected,

        -- flag-then-sum unique (per date×campaign×agent×phone) — additive at this grain only
        COUNT(*) FILTER (WHERE rn_u=1)                                              AS ch_unique_dialled,
        COUNT(*) FILTER (WHERE rn_uc=1 AND system_disposition='CONNECTED')          AS ch_unique_connected,

        COUNT(*) FILTER (WHERE attempt_number=1)                                    AS ch_first_attempt,
        COUNT(*) FILTER (WHERE attempt_number=1 AND system_disposition='CONNECTED') AS ch_first_attempt_connected,
        COUNT(*) FILTER (WHERE system_disposition='CONNECTED' AND talk_sec>30)      AS ch_successful_connect,
        COUNT(*) FILTER (WHERE disposition_class='Interested')                      AS ch_interested,
        COUNT(*) FILTER (WHERE disposition_code IS NOT NULL
                         AND disposition_code NOT IN ('wrap.timeout','user.forced.logged.off')) AS ch_tagged,
        COUNT(*) FILTER (WHERE disposition_class='Voicemail')                       AS ch_voicemail,
        COUNT(*) FILTER (WHERE NULLIF(trim(customer_hold_duration),'')::interval > interval '0') AS ch_answered_hold_calls,
        COUNT(*) FILTER (WHERE system_disposition='CONNECTED'
                         AND NULLIF(trim(user_talk_time),'')::interval < interval '60 sec')      AS ch_short_calls,

        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(user_talk_time),'')::interval),0))::bigint         AS ch_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(customer_talk_time),'')::interval),0))::bigint     AS ch_cust_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(acw_duration),'')::interval),0))::bigint           AS ch_acw_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(customer_hold_duration),'')::interval),0))::bigint AS ch_hold_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(ivr_time),'')::interval),0))::bigint               AS ch_ivr_secs

    FROM ch_base
    GROUP BY 1,2,3
),

-- SQL feed (client; date×agent — NO campaign per spec). Empty until loaded → all sql_allocated = 0.
sq AS (
    SELECT 
        report_date, 
        lower(trim(user_id)) AS agent_email, 
        SUM(sql) AS sql

    FROM sql_manual
    WHERE user_id IS NOT NULL AND trim(user_id) <> ''
    GROUP BY 1,2),

-- backbone keys = productivity ∪ call activity
keys AS (
    SELECT report_date, agent_email, campaign_name FROM ap
    UNION
    SELECT report_date, agent_email, campaign_name FROM ch )

SELECT
    k.report_date,
    k.agent_email,
    k.campaign_name,

    CASE WHEN k.campaign_name ILIKE '%ASR%' THEN 'Amritsar' ELSE 'Gurgaon' END  AS location,

    'Week-' || (FLOOR((EXTRACT(DAY FROM k.report_date)
              + EXTRACT(ISODOW FROM date_trunc('month', k.report_date)) - 2)/7)+1)::int::text AS week,

    'eulermotors'                                                               AS tenant_name,
    'maxicus'                                                                   AS entity_name,

    -- APR raw
    ap.ap_intervals, 
    ap.ap_staffed_secs, 
    ap.ap_ready_secs, 
    ap.ap_break_secs, 
    ap.ap_idle_secs, 
    ap.ap_service_secs,
    ap.ap_talk_secs, 
    ap.ap_acw_secs, 
    ap.ap_hold_secs, 
    ap.ap_ring_secs, 
    ap.ap_wrapped_calls,
    ap.ap_auto_dials, 
    ap.ap_auto_preview_dials, 
    ap.ap_inbound_received, 
    ap.ap_manual_dials, 
    ap.ap_manual_preview_dials,
    ap.ap_callbacks_received, 
    ap.ap_transfers_received,
    ap.ap_connected_auto, 
    ap.ap_connected_inbound, 
    ap.ap_connected_manual, 
    ap.ap_connected_callbacks,
    ap.ap_connected_manual_preview, 
    ap.ap_connected_auto_preview, 
    ap.ap_click_to_calls, 
    ap.ap_connected_click_to_calls,
    ap.ap_connected_transfers,

    (ap.ap_auto_dials + ap.ap_auto_preview_dials + ap.ap_inbound_received +
     ap.ap_manual_dials + ap.ap_manual_preview_dials + ap.ap_callbacks_received)  AS ap_total_offered,

    (ap.ap_connected_auto + ap.ap_connected_inbound + ap.ap_connected_manual +
     ap.ap_connected_manual_preview + ap.ap_connected_auto_preview + ap.ap_click_to_calls) AS ap_total_answered,

    (ap.ap_talk_secs + ap.ap_acw_secs)                              AS ap_tht,

    -- 8h cap on the agent's WHOLE day, split across campaigns by ready-share (additive)
    COALESCE(
        LEAST(SUM(COALESCE(ap.ap_ready_secs,0)) OVER (PARTITION BY k.report_date, k.agent_email), 28800)
        * COALESCE(ap.ap_ready_secs,0)::numeric
        / NULLIF(SUM(COALESCE(ap.ap_ready_secs,0)) OVER (PARTITION BY k.report_date, k.agent_email), 0)
    , 0)                                                                          AS ap_capped_ready_secs,

    -- call_history pivots
    COALESCE(ch.ch_calls,0) ch_calls, 
    COALESCE(ch.ch_inbound_calls,0) ch_inbound_calls,
    COALESCE(ch.ch_outbound_calls,0) ch_outbound_calls, 
    COALESCE(ch.ch_connected,0) ch_connected,
    COALESCE(ch.ch_not_connected,0) ch_not_connected,
    COALESCE(ch.ch_unique_dialled,0) ch_unique_dialled, 
    COALESCE(ch.ch_unique_connected,0) ch_unique_connected,
    COALESCE(ch.ch_first_attempt,0) ch_first_attempt, 
    COALESCE(ch.ch_first_attempt_connected,0) ch_first_attempt_connected,
    COALESCE(ch.ch_successful_connect,0) ch_successful_connect, 
    COALESCE(ch.ch_interested,0) ch_interested,
    COALESCE(ch.ch_tagged,0) ch_tagged, 
    COALESCE(ch.ch_voicemail,0) ch_voicemail,
    COALESCE(ch.ch_answered_hold_calls,0) ch_answered_hold_calls, 
    COALESCE(ch.ch_short_calls,0) ch_short_calls,
    COALESCE(ch.ch_talk_secs,0) ch_talk_secs, 
    COALESCE(ch.ch_cust_talk_secs,0) ch_cust_talk_secs,
    COALESCE(ch.ch_acw_secs,0) ch_acw_secs, 
    COALESCE(ch.ch_hold_secs,0) ch_hold_secs,
    COALESCE(ch.ch_ivr_secs,0) ch_ivr_secs,

    -- login share = capped ready / 8h   (1.0 = one full agent shift; sums to ≤1 per agent-day)
    COALESCE(
        LEAST(SUM(COALESCE(ap.ap_ready_secs,0)) OVER (PARTITION BY k.report_date, k.agent_email), 28800)
        * COALESCE(ap.ap_ready_secs,0)::numeric
        / NULLIF(SUM(COALESCE(ap.ap_ready_secs,0)) OVER  (PARTITION BY k.report_date, k.agent_email), 0)
    , 0) / 28800.0                                                                AS login_count,

    -- SQL allocated across the agent's campaigns by connects (sum over campaigns = agent's true SQL)
    CASE
        WHEN COALESCE(sq.sql,0) = 0 
            THEN 0
        WHEN SUM(COALESCE(ch.ch_connected,0)) OVER (PARTITION BY k.report_date, k.agent_email) > 0
            THEN COALESCE(sq.sql,0) * COALESCE(ch.ch_connected,0)::numeric
                 / SUM(COALESCE(ch.ch_connected,0)) OVER (PARTITION BY k.report_date, k.agent_email)
        ELSE COALESCE(sq.sql,0)::numeric / COUNT(*) OVER (PARTITION BY k.report_date, k.agent_email)
    END                                                                           AS sql_allocated

FROM keys k
LEFT JOIN ap 
    ON ap.report_date=k.report_date AND ap.agent_email=k.agent_email AND ap.campaign_name=k.campaign_name
LEFT JOIN ch 
    ON ch.report_date=k.report_date AND ch.agent_email=k.agent_email AND ch.campaign_name=k.campaign_name
LEFT JOIN sq 
    ON sq.report_date=k.report_date AND sq.agent_email=k.agent_email

WHERE k.report_date > '{last_processed}'
  AND k.report_date <= '{high_water_mark}'



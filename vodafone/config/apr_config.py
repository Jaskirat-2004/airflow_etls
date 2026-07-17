# JS =============================================================================================================== JS
#                                       QUERIES FOR APR REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

VODAFONE_FACT_APR_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS vodafone.vodafone_fact_apr_report
(
    report_date            Date,
    week                   String,
    emp_id                 String,
    emp_name               Nullable(String),
    tenant_name            String,
    entity_name            String,
    process                Nullable(String),
    campaign               Nullable(String),
    designation            Nullable(String),
    grade                  Nullable(String),
    employee_type          Nullable(String),
    team_leader            Nullable(String),
    functional_manager     Nullable(String),
    location               Nullable(String),
    department             Nullable(String),
    current_status         Nullable(String),
    doj                    Nullable(Date),
    ap_staffed_secs        Int32,
    ap_ready_secs          Int32,
    ap_break_secs          Int32,
    ap_idle_secs           Int32,
    ap_talk_secs           Int32,
    ap_wrap_secs           Int32,
    ap_hold_secs           Int32,
    ap_ring_secs           Int32,
    ap_preview_secs        Int32,
    ap_auto_call_on_secs   Int32,
    ap_auto_call_off_secs  Int32,
    ap_tht_secs            Int32,
    ap_acd_secs            Int32,
    on_calls               Int32,
    off_calls              Int32,
    calls                  Int32,
    inbound_calls          Int32,
    manual_calls           Int32,
    dialer_calls           Int32,
    callback_calls         Int32,
    transfer_calls         Int32,
    login_count            UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, emp_id)

"""

# JS ======================================= FACT TABLE ======================================= JS


VODAFONE_FACT_APR_REPORT_QUERY = """

-- Single aggregation CTE: parse durations + sum call-type counts directly, grouped to the fact grain
-- (date x emp x campaign). HC dims joined in the final SELECT.
-- (custom dump is already daily & unique on this grain; GROUP BY is defensive / future-proof for 30-min exports.)
WITH agg AS (
    SELECT
        report_date,
        split_part(user_id,'@',1)                                                          AS emp_id,
        campaign_name,
        MAX(process_name)                                                                  AS process_name,

        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_staffed_duration,'')::interval)::int),0)         AS staffed_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_ready_duration,'')::interval)::int),0)           AS ready_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_break_duration,'')::interval)::int),0)           AS break_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_idle_time,'')::interval)::int),0)                AS idle_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_talk_time_in_interval,'')::interval)::int),0)    AS talk_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_wrap_time_in_interval,'')::interval)::int),0)    AS wrap_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_hold_time,'')::interval)::int),0)                AS hold_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_ring_time,'')::interval)::int),0)                AS ring_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_preview_time,'')::interval)::int),0)             AS preview_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(auto_call_on_duration,'')::interval)::int),0)          AS auto_call_on_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(auto_call_off_duration,'')::interval)::int),0)         AS auto_call_off_secs,

        (COALESCE(SUM(auto_call_on_dialer_calls),0)   + COALESCE(SUM(auto_call_off_dialer_calls),0))    AS dialer_calls,
        (COALESCE(SUM(auto_call_on_inbound_calls),0)  + COALESCE(SUM(auto_call_off_inbound_calls),0))   AS inbound_calls,
        (COALESCE(SUM(auto_call_on_manual_calls),0)   + COALESCE(SUM(auto_call_off_manual_calls),0))    AS manual_calls,
        (COALESCE(SUM(auto_call_on_callback_calls),0) + COALESCE(SUM(auto_call_off_callback_calls),0))  AS callback_calls,
        (COALESCE(SUM(auto_call_on_transfer_to_campaign_calls),0) + COALESCE(SUM(auto_call_off_transfer_to_campaign_calls),0)) AS transfer_calls,

        (COALESCE(SUM(auto_call_on_dialer_calls),0) + COALESCE(SUM(auto_call_on_inbound_calls),0) + COALESCE(SUM(auto_call_on_manual_calls),0)
            + COALESCE(SUM(auto_call_on_callback_calls),0) + COALESCE(SUM(auto_call_on_transfer_to_campaign_calls),0))    AS on_calls,
        (COALESCE(SUM(auto_call_off_dialer_calls),0) + COALESCE(SUM(auto_call_off_inbound_calls),0) + COALESCE(SUM(auto_call_off_manual_calls),0)
            + COALESCE(SUM(auto_call_off_callback_calls),0) + COALESCE(SUM(auto_call_off_transfer_to_campaign_calls),0))  AS off_calls

    FROM custom_agent_productivity_interval_summary
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1,2,3
)

SELECT
    a.report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM a.report_date)/7.0)::int          AS week,
    a.emp_id,
    h.employee_name                                                    AS emp_name,
    'vodafone'                                                         AS tenant_name,
    'maxicus'                                                          AS entity_name,
    COALESCE(h.ou_name, a.process_name)                                AS process,
    a.campaign_name                                                    AS campaign,
    h.designation_name                                                 AS designation,
    h.grade,
    h.employee_type,
    h.reporting_to_name                                                AS team_leader,
    h.functional_reporting_to_name                                     AS functional_manager,
    h.location_name                                                    AS location,
    h.department_name                                                  AS department,
    h.current_status,
    h.date_of_joining                                                  AS doj,

    a.staffed_secs                                                     AS ap_staffed_secs,
    a.ready_secs                                                       AS ap_ready_secs,
    a.break_secs                                                       AS ap_break_secs,
    a.idle_secs                                                        AS ap_idle_secs,
    a.talk_secs                                                        AS ap_talk_secs,
    a.wrap_secs                                                        AS ap_wrap_secs,
    a.hold_secs                                                        AS ap_hold_secs,
    a.ring_secs                                                        AS ap_ring_secs,
    a.preview_secs                                                     AS ap_preview_secs,
    a.auto_call_on_secs                                                AS ap_auto_call_on_secs,
    a.auto_call_off_secs                                               AS ap_auto_call_off_secs,

    (a.talk_secs + a.wrap_secs + a.hold_secs)                          AS ap_tht_secs,
    (a.talk_secs + a.wrap_secs + a.ring_secs + a.preview_secs + a.hold_secs) AS ap_acd_secs,

    a.on_calls,
    a.off_calls,
    (a.on_calls + a.off_calls)                                         AS calls,
    a.inbound_calls,
    a.manual_calls,
    a.dialer_calls,
    a.callback_calls,
    a.transfer_calls,
    1                                                                  AS login_count

FROM agg a
LEFT JOIN vodafone_head_count h
    ON h.report_date = a.report_date AND h.employee_id = a.emp_id

"""

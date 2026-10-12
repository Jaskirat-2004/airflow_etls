# JS =============================================================================================================== JS
#                                       QUERIES FOR APR REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

VODAFONE_FACT_FTE_REPORT_DDL = """


CREATE TABLE IF NOT EXISTS vodafone.vodafone_fact_fte_report
(
    report_date            Date,
    week                   String,
    emp_id                 String,
    emp_name               Nullable(String),
    tenant_name            String,
    entity_name            String,
    process                Nullable(String),
    campaign               Nullable(String),
    call_type              String,
    designation            Nullable(String),
    grade                  Nullable(String),
    employee_type          Nullable(String),
    team_leader            Nullable(String),
    functional_manager     Nullable(String),
    location               Nullable(String),
    department             Nullable(String),
    current_status         Nullable(String),
    doj                    Nullable(Date),
    staffed_secs           Int32,
    ready_secs             Int32,
    break_secs             Int32,
    idle_secs              Int32,
    talk_secs              Int32,
    acw_secs               Int32,
    hold_secs              Int32,
    ring_secs              Int32,
    auto_call_on_secs      Int32,
    auto_call_off_secs     Int32,
    auto_dials             Int32,
    inbound_received       Int32,
    manual_dials           Int32,
    callbacks_received     Int32,
    transfers_received     Int32,
    total_dials            Int32,
    connected_auto         Int32,
    connected_inbound      Int32,
    connected_manual       Int32,
    connected_callbacks    Int32,
    connected_transfers    Int32,
    total_connected        Int32,
    wrapped_calls          Int32,
    is_primary_campaign    UInt8,
    fte_capped_ready_secs  Int32,
    hc_flag                UInt8
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, emp_id)
"""

# JS ======================================= FACT TABLE ======================================= JS


VODAFONE_FACT_FTE_REPORT_QUERY = """

WITH camp AS (
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
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_acw_duration_in_interval,'')::interval)::int),0) AS acw_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_customer_hold_duration,'')::interval)::int),0)   AS hold_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_ring_time,'')::interval)::int),0)                AS ring_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(auto_call_on_duration,'')::interval)::int),0)          AS auto_call_on_secs,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(auto_call_off_duration,'')::interval)::int),0)         AS auto_call_off_secs,

        COALESCE(SUM(auto_dials),0)                                                        AS auto_dials,
        COALESCE(SUM(inbound_received),0)                                                  AS inbound_received,
        COALESCE(SUM(manual_dials),0)                                                      AS manual_dials,
        COALESCE(SUM(callbacks_received),0)                                                AS callbacks_received,
        COALESCE(SUM(transfers_received),0)                                                AS transfers_received,
        (COALESCE(SUM(auto_dials),0) + COALESCE(SUM(inbound_received),0) + COALESCE(SUM(manual_dials),0)
         + COALESCE(SUM(callbacks_received),0) + COALESCE(SUM(transfers_received),0))      AS total_dials,

        COALESCE(SUM(connected_auto_dials),0)                                              AS connected_auto,
        COALESCE(SUM(connected_inbound),0)                                                 AS connected_inbound,
        COALESCE(SUM(connected_manual_dials),0)                                            AS connected_manual,
        COALESCE(SUM(connected_callbacks),0)                                               AS connected_callbacks,
        COALESCE(SUM(connected_transfers),0)                                               AS connected_transfers,
        (COALESCE(SUM(connected_auto_dials),0) + COALESCE(SUM(connected_inbound),0) + COALESCE(SUM(connected_manual_dials),0)
         + COALESCE(SUM(connected_callbacks),0) + COALESCE(SUM(connected_transfers),0))    AS total_connected,

        COALESCE(SUM(COALESCE(total_wrapped_calls,0)),0)                                   AS wrapped_calls

    FROM agent_productivity_interval_summary
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1,2,3
),

alloc AS (   -- agent-day window: total ready, proportional FTE cap, agent-day flag
    SELECT
        camp.*,
        SUM(ready_secs) OVER (PARTITION BY report_date, emp_id)                             AS day_ready_secs,
        COALESCE(ROUND( ready_secs::numeric
               * LEAST(SUM(ready_secs) OVER (PARTITION BY report_date, emp_id), 36000)
               / NULLIF(SUM(ready_secs) OVER (PARTITION BY report_date, emp_id), 0) )::int, 0)  AS fte_capped_ready_secs,
        (ROW_NUMBER() OVER (PARTITION BY report_date, emp_id ORDER BY ready_secs DESC NULLS LAST) = 1)::int AS is_primary_campaign
    FROM camp
)

SELECT
    a.report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM a.report_date)/7.0)::int          AS week,
    a.emp_id,
    h.employee_name                                                    AS emp_name,
    'vodafone'                                                         AS tenant_name,
    'maxicus'                                                          AS entity_name,
    COALESCE(h.ou_name, a.process_name)                               AS process,
    a.campaign_name                                                    AS campaign,
    CASE WHEN a.campaign_name = 'Chat_In' THEN 'Inbound' ELSE 'Outbound' END AS call_type,   -- OB/IB filter (Chat_In=IB, rest=OB)
    h.designation_name                                                 AS designation,
    h.grade,
    h.employee_type,
    h.reporting_to_name                                                AS team_leader,
    h.functional_reporting_to_name                                     AS functional_manager,
    h.location_name                                                    AS location,
    h.department_name                                                  AS department,
    h.current_status,
    h.date_of_joining                                                  AS doj,

    a.staffed_secs,
    a.ready_secs,
    a.break_secs,
    a.idle_secs,
    a.talk_secs,
    a.acw_secs,
    a.hold_secs,
    a.ring_secs,
    a.auto_call_on_secs,
    a.auto_call_off_secs,

    a.auto_dials,
    a.inbound_received,
    a.manual_dials,
    a.callbacks_received,
    a.transfers_received,
    a.total_dials,
    a.connected_auto,
    a.connected_inbound,
    a.connected_manual,
    a.connected_callbacks,
    a.connected_transfers,
    a.total_connected,
    a.wrapped_calls,

    a.is_primary_campaign,
    a.fte_capped_ready_secs,
    (h.employee_id IS NOT NULL)::int                                   AS hc_flag

FROM alloc a
LEFT JOIN vodafone_head_count h ON h.report_date = a.report_date AND h.employee_id = a.emp_id

"""


# JS =============================================================================================================== JS
#                        QUERIES FOR CALL DETAILS FACT TABLE  (Call Disconnection + CLI Repeat)
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

YOUBROADBAND_FACT_CALL_DETAILS_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS youbroadband.youbroadband_fact_call_details_report
(
    report_date              Date,
    week                     String,
    tenant_name              String,
    entity_name              String,

    hc_agent_name            String,
    hc_employee_id           String,
    hc_grade                 String,
    hc_designation           String,
    hc_tl_name               String,
    hc_location              String,

    cd_user_id               String,
    cd_queue_name            String,
    cd_call_type             String,
    cd_system_disposition    String,
    cd_hangup_details        String,

    cd_attempted             UInt32,
    cd_connected             UInt32,
    cd_agent_hangup          UInt32,
    cd_customer_hangup       UInt32,
    cd_system_hangup         UInt32,

    cd_rpt_1day              UInt32,
    cd_rpt_24hrs             UInt32,
    cd_rpt_3day              UInt32,

    cd_talk_secs             UInt32,
    cd_hold_secs             UInt32,
    cd_acw_secs              UInt32,
    cd_ivr_secs              UInt32,

    loaded_at                DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, cd_user_id)

"""

# JS ======================================= QUERY ======================================= JS

YOUBROADBAND_FACT_CALL_DETAILS_REPORT_QUERY = """

WITH cd AS (
    SELECT
        cd.report_date,
        cd.call_id,
        cd.call_time,
        TRIM(cd.user_id)                                           AS cd_user_id,
        COALESCE(NULLIF(TRIM(cd.queue_name),''),'Blank')           AS cd_queue_name,
        COALESCE(NULLIF(TRIM(cd.call_type),''),'Blank')            AS cd_call_type,
        COALESCE(NULLIF(TRIM(cd.system_disposition),''),'Blank')   AS cd_system_disposition,
        COALESCE(NULLIF(TRIM(cd.hangup_details),''),'Blank')       AS cd_hangup_details,
        RIGHT(REGEXP_REPLACE(cd.phone,'\\D','','g'),10)            AS phone_10,
        COALESCE(EXTRACT(EPOCH FROM NULLIF(TRIM(cd.customer_talk_time),'')::interval),0)::int     AS cd_talk_secs,
        COALESCE(EXTRACT(EPOCH FROM NULLIF(TRIM(cd.customer_hold_duration),'')::interval),0)::int AS cd_hold_secs,
        COALESCE(EXTRACT(EPOCH FROM NULLIF(TRIM(cd.acw_duration),'')::interval),0)::int           AS cd_acw_secs,
        COALESCE(EXTRACT(EPOCH FROM NULLIF(TRIM(cd.ivr_time),'')::interval),0)::int               AS cd_ivr_secs
    FROM call_details cd
    WHERE cd.report_date >  DATE '{last_processed}' - 3
      AND cd.report_date <= DATE '{high_water_mark}'
      AND NULLIF(TRIM(cd.user_id),'') IS NOT NULL
),

hc AS (
    SELECT
        report_date                                         AS hc_report_date,
        TRIM(employee_id)                                   AS hc_employee_id,
        COALESCE(NULLIF(TRIM(employee_name),''),'NA')       AS hc_agent_name,
        COALESCE(NULLIF(TRIM(grade),''),'NA')               AS hc_grade,
        COALESCE(NULLIF(TRIM(designation_name),''),'NA')    AS hc_designation,
        COALESCE(NULLIF(TRIM(reporting_to_name),''),'NA')   AS hc_tl_name,
        COALESCE(NULLIF(TRIM(location_name),''),'NA')       AS hc_location
    FROM head_count
    WHERE TRIM(grade) = 'G1'
),

g1 AS (
    SELECT cd.*
    FROM cd
    JOIN hc ON hc.hc_report_date  = cd.report_date
           AND hc.hc_employee_id = cd.cd_user_id
),

rpt AS (
    SELECT
        call_id,
        CASE WHEN prev_ts IS NOT NULL AND report_date = prev_date                 THEN 1 ELSE 0 END AS cd_rpt_1day,
        CASE WHEN prev_ts IS NOT NULL AND call_time - prev_ts <= INTERVAL '1 day' THEN 1 ELSE 0 END AS cd_rpt_24hrs,
        CASE WHEN prev_ts IS NOT NULL AND report_date - prev_date < 3             THEN 1 ELSE 0 END AS cd_rpt_3day
    FROM (
        SELECT
            call_id,
            report_date,
            call_time,
            LAG(call_time)   OVER w AS prev_ts,
            LAG(report_date) OVER w AS prev_date
        FROM g1
        WHERE cd_system_disposition = 'CONNECTED'
        WINDOW w AS (PARTITION BY phone_10 ORDER BY call_time)
    ) z
),

agg AS (
    SELECT
        g.report_date,
        g.cd_user_id,
        g.cd_queue_name,
        g.cd_call_type,
        g.cd_system_disposition,
        g.cd_hangup_details,

        COUNT(*)                                                               AS cd_attempted,
        SUM(CASE WHEN g.cd_system_disposition = 'CONNECTED' THEN 1 ELSE 0 END)  AS cd_connected,
        SUM(CASE WHEN g.cd_system_disposition = 'CONNECTED'
                  AND g.cd_hangup_details IN ('AGENT_HANGUP_PHONE','AGENT_HANGUP_UI','CUSTOMER_HANGUP_UI')
                 THEN 1 ELSE 0 END)                                            AS cd_agent_hangup,
        SUM(CASE WHEN g.cd_system_disposition = 'CONNECTED'
                  AND g.cd_hangup_details = 'CUSTOMER_HANGUP_PHONE'
                 THEN 1 ELSE 0 END)                                            AS cd_customer_hangup,
        SUM(CASE WHEN g.cd_system_disposition = 'CONNECTED'
                  AND g.cd_hangup_details IN ('SYSTEM_HANGUP','SYSTEM_MEDIA')
                 THEN 1 ELSE 0 END)                                            AS cd_system_hangup,

        SUM(COALESCE(r.cd_rpt_1day,0))                                         AS cd_rpt_1day,
        SUM(COALESCE(r.cd_rpt_24hrs,0))                                        AS cd_rpt_24hrs,
        SUM(COALESCE(r.cd_rpt_3day,0))                                         AS cd_rpt_3day,

        SUM(g.cd_talk_secs)                                                    AS cd_talk_secs,
        SUM(g.cd_hold_secs)                                                    AS cd_hold_secs,
        SUM(g.cd_acw_secs)                                                     AS cd_acw_secs,
        SUM(g.cd_ivr_secs)                                                     AS cd_ivr_secs

    FROM g1 g
    LEFT JOIN rpt r ON r.call_id = g.call_id
    WHERE g.report_date > DATE '{last_processed}'
    GROUP BY 1,2,3,4,5,6
)

SELECT
    a.report_date,
    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM a.report_date)/7.0),4)::int AS week,
    'youbroadband'            AS tenant_name,
    'maxicus'                 AS entity_name,

    hc.hc_agent_name,
    hc.hc_employee_id,
    hc.hc_grade,
    hc.hc_designation,
    hc.hc_tl_name,
    hc.hc_location,

    a.cd_user_id,
    a.cd_queue_name,
    a.cd_call_type,
    a.cd_system_disposition,
    a.cd_hangup_details,

    a.cd_attempted,
    a.cd_connected,
    a.cd_agent_hangup,
    a.cd_customer_hangup,
    a.cd_system_hangup,

    a.cd_rpt_1day,
    a.cd_rpt_24hrs,
    a.cd_rpt_3day,

    a.cd_talk_secs,
    a.cd_hold_secs,
    a.cd_acw_secs,
    a.cd_ivr_secs

FROM agg a
LEFT JOIN hc ON hc.hc_report_date  = a.report_date
            AND hc.hc_employee_id = a.cd_user_id

"""

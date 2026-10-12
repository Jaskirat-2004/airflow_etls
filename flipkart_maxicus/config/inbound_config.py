# JS =============================================================================================================== JS
#                                       QUERIES FOR INBOUND REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

YOUBROADBAND_FACT_INBOUND_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS youbroadband.youbroadband_fact_inbound_report
(
    report_date              Date,
    week                     String,
    tenant_name              String,
    entity_name              String,
    total_offered            Int32,
    total_answered           Int32,
    total_abandon            Int32,
    unique_customer          Int32,
    multiple_customer        Int32,
    multiple_customer_calls  Int32,
    unique_answered          Int32,
    abd_working              Int32,
    abd_nonworking           Int32,
    total_wait_secs          Int64,
    connected                Int32,
    connected_in_target      Int32,
    tagging_count            Int32
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date)

"""


# JS ======================================= FACT TABLE ======================================= JS


YOUBROADBAND_FACT_INBOUND_REPORT_QUERY = """

WITH ph AS (
    SELECT 
        report_date, 
        phone,
        count(*)                                            AS n,
        count(*) FILTER (WHERE answered_hungup='ANSWERED')  AS na

    FROM acd_call_details
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY report_date, phone
),

cust AS (
    SELECT 
        report_date,
        count(*) FILTER (WHERE n=1)::int               AS unique_customer,
        count(*) FILTER (WHERE n>1)::int               AS multiple_customer,
        COALESCE(SUM(n) FILTER (WHERE n>1),0)::int     AS multiple_customer_calls,
        count(*) FILTER (WHERE na>0)::int              AS unique_answered

    FROM ph
    GROUP BY report_date
),

acd AS (
    SELECT 
        report_date,
        count(*)::int                                              AS total_offered,
        (count(*) FILTER (WHERE answered_hungup='ANSWERED'))::int  AS total_answered,
        (count(*) FILTER (WHERE answered_hungup='HUNGUP'))::int    AS total_abandon,
        COALESCE(SUM(EXTRACT(EPOCH FROM NULLIF(total_wait_time,'')::interval)),0)::bigint AS total_wait_secs

    FROM acd_call_details
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY report_date
),

pool AS (
    SELECT 
        report_date,
        (count(*) FILTER (WHERE answered_hungup='HUNGUP' AND call_time::time BETWEEN TIME '09:00:00' AND TIME '20:45:00'))::int     AS abd_working,
        (count(*) FILTER (WHERE answered_hungup='HUNGUP' AND call_time::time NOT BETWEEN TIME '09:00:00' AND TIME '20:45:00'))::int AS abd_nonworking
    FROM custom_pool_report
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY report_date
),

iv AS (
    SELECT 
        report_date,
        COALESCE(SUM(total_connected_calls),0)::int     AS connected,
        COALESCE(SUM(total_connected_in_target),0)::int AS connected_in_target

    FROM acd_call_interval_summary
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY report_date
),

tag AS (
    SELECT 
        report_date, 
        count(*)::int AS tagging_count
    FROM custom_tagging
    WHERE category = 'Inbound' AND report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY report_date
)

SELECT
    a.report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM a.report_date)/7.0)::int    AS week,
    'youbroadband'                                                   AS tenant_name,
    'maxicus'                                                    AS entity_name,
    a.total_offered,
    a.total_answered,
    a.total_abandon,
    COALESCE(c.unique_customer,0)                               AS unique_customer,
    COALESCE(c.multiple_customer,0)                             AS multiple_customer,
    COALESCE(c.multiple_customer_calls,0)                       AS multiple_customer_calls,
    COALESCE(c.unique_answered,0)                               AS unique_answered,
    COALESCE(p.abd_working,0)                                   AS abd_working,
    COALESCE(p.abd_nonworking,0)                                AS abd_nonworking,
    a.total_wait_secs,
    COALESCE(iv.connected,0)                                    AS connected,
    COALESCE(iv.connected_in_target,0)                          AS connected_in_target,
    COALESCE(t.tagging_count,0)                                 AS tagging_count

FROM acd a
LEFT JOIN cust c 
    ON c.report_date  = a.report_date
LEFT JOIN pool p 
    ON p.report_date  = a.report_date
LEFT JOIN iv    
    ON iv.report_date = a.report_date
LEFT JOIN tag t  
    ON t.report_date  = a.report_date

"""

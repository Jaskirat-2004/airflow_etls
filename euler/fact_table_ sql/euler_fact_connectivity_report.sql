
WITH ch AS (
  SELECT
    call_time::date                                                                AS report_date,
    campaign_name,
    CASE WHEN campaign_name ILIKE '%ASR%' THEN 'Amritsar' ELSE 'Gurgaon' END       AS location,

    call_type, 
    lead_name, 
    phone,
    
    EXTRACT(EPOCH FROM NULLIF(user_setup_time,'')::interval)                       AS user_setup_sec,
    EXTRACT(EPOCH FROM NULLIF(customer_setup_time,'')::interval)                   AS cust_setup_sec,
    EXTRACT(EPOCH FROM NULLIF(user_ringing_time,'')::interval)                     AS user_ring_sec,
    EXTRACT(EPOCH FROM NULLIF(customer_ringing_time,'')::interval)                 AS cust_ring_sec,
    EXTRACT(EPOCH FROM NULLIF(ivr_time,'')::interval)                              AS ivr_sec,
    EXTRACT(EPOCH FROM NULLIF(user_talk_time,'')::interval)                        AS talk_sec,
    EXTRACT(EPOCH FROM NULLIF(customer_talk_time,'')::interval)                    AS cust_talk_sec,
    EXTRACT(EPOCH FROM NULLIF(customer_hold_duration,'')::interval)                AS hold_sec,
    EXTRACT(EPOCH FROM NULLIF(acw_duration,'')::interval)                          AS acw_sec,

    -- Unique Calls
    row_number() OVER (PARTITION BY call_time::date, campaign_name, phone
                        ORDER BY call_time, call_id)                               AS rn_camp,

    row_number() OVER (PARTITION BY call_time::date, campaign_name, phone,
                                    (system_disposition='CONNECTED')
                        ORDER BY call_time, call_id)                               AS rn_camp_conn
  
  FROM call_history
)

SELECT
  report_date,
  'Week-' || (FLOOR((EXTRACT(DAY FROM report_date)
            + EXTRACT(ISODOW FROM date_trunc('month', report_date)) - 2)/7)+1)::int::text AS week,

  campaign_name,
  location,

  'eulermotors'                                                       AS tenant_name,
  'maxicus'                                                           AS entity_name,

  count(*)                                                            AS ch_attempted,
  count(*) FILTER (WHERE system_disposition='CONNECTED')              AS ch_connected,

  count(*) FILTER (WHERE rn_camp=1)                                         AS ch_unique_attempted,
  count(*) FILTER (WHERE rn_camp_conn=1 AND system_disposition='CONNECTED') AS ch_unique_connected,
  count(*) FILTER (WHERE rn_camp=1 AND system_disposition='CONNECTED')      AS ch_first_attempt_connected,

  count(*) FILTER (WHERE system_disposition='CONNECTED' AND talk_sec>30)    AS ch_successful_connect,

  count(*) FILTER (WHERE talk_sec>0  AND talk_sec<3)                  AS ch_sc_lt3,
  count(*) FILTER (WHERE talk_sec>=3 AND talk_sec<=15)                AS ch_sc_3_15,
  count(*) FILTER (WHERE talk_sec>=16 AND talk_sec<=30)               AS ch_sc_16_30,
  count(*) FILTER (WHERE talk_sec>=31 AND talk_sec<=60)               AS ch_sc_31_60,

  count(*) FILTER (WHERE call_type='outbound.auto.dial')              AS ch_auto_dials,
  count(*) FILTER (WHERE call_type='outbound.callback.dial')          AS ch_callback_dials,
  count(*) FILTER (WHERE call_type='inbound.call.dial')               AS ch_inbound_calls,
  count(*) FILTER (WHERE call_type='outbound.manual.dial')            AS ch_manual_dials,

  count(*) FILTER (WHERE lead_name LIKE 'Prod%')                      AS ch_calls_prod,
  count(*) FILTER (WHERE lead_name NOT LIKE 'Prod%' OR lead_name IS NULL) AS ch_calls_manual,

  COALESCE(SUM(user_setup_sec),0)::bigint           AS ch_user_setup_secs,
  COALESCE(SUM(cust_setup_sec),0)::bigint           AS ch_cust_setup_secs,
  COALESCE(SUM(user_ring_sec) ,0)::bigint           AS ch_user_ring_secs,
  COALESCE(SUM(cust_ring_sec) ,0)::bigint           AS ch_cust_ring_secs,
  COALESCE(SUM(ivr_sec)       ,0)::bigint           AS ch_ivr_secs,
  COALESCE(SUM(talk_sec)      ,0)::bigint           AS ch_talk_secs,
  COALESCE(SUM(cust_talk_sec) ,0)::bigint           AS ch_cust_talk_secs,
  COALESCE(SUM(hold_sec)      ,0)::bigint           AS ch_hold_secs,
  COALESCE(SUM(acw_sec)       ,0)::bigint           AS ch_acw_secs

FROM ch

WHERE report_date > '{last_processed}' 
  AND report_date <= '{high_water_mark}'

GROUP BY report_date, campaign_name,location;

-- ======================================================================
-- ======================================================================
-- ======================================================================
-- ======================================================================


DDL

CREATE TABLE IF NOT EXISTS eulermotors.euler_fact_connectivity_report
(
  report_date                   Date, 
  week                          String, 
  campaign_name                 String, 
  location                      String, 
  tenant_name                   String, 
  entity_name                   String,
  ch_attempted                  Int32, 
  ch_connected                  Int32, 
  ch_unique_attempted           Int32, 
  ch_unique_connected           Int32,
  ch_first_attempt_connected    Int32, 
  ch_successful_connect         Int32,
  ch_sc_lt3                     Int32, 
  ch_sc_3_15                    Int32, 
  ch_sc_16_30                   Int32, 
  ch_sc_31_60                   Int32,
  ch_auto_dials                 Int32, 
  ch_callback_dials             Int32, 
  ch_inbound_calls              Int32, 
  ch_manual_dials               Int32,
  ch_calls_prod                 Int32, 
  ch_calls_manual               Int32,
  ch_user_setup_secs            Int64, 
  ch_cust_setup_secs            Int64, 
  ch_user_ring_secs             Int64, 
  ch_cust_ring_secs             Int64,
  ch_ivr_secs                   Int64, 
  ch_talk_secs                  Int64, 
  ch_cust_talk_secs             Int64, 
  ch_hold_secs                  Int64, 
  ch_acw_secs                   Int64
)
ENGINE = MergeTree() 
ORDER BY (report_date, campaign_name);
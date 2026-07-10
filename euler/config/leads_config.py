# JS =============================================================================================================== JS
#                                       QUERIES FOR LEADS REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

EULER_FACT_LEADS_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS eulermotors.euler_fact_leads_report
(
  report_date          Date,
  source               String,
  location             String,
  week                 String,
  tenant_name          String,
  entity_name          String,
  leads_received       Int32,
  leads_dialed         Int32,
  leads_not_dialed     Int32,
  leads_connected      Int32,
  leads_successful     Int32,
  leads_interested     Int32,
  lead_attempts        Int64,
  lead_connected_calls Int64,
  lead_talk_secs       Int64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, source, location)

"""

# JS ======================================= FACT TABLE ======================================= JS

EULER_FACT_LEADS_REPORT_QUERY = """

-- call_history aggregated to (date, phone) — one row per dialed number per day
WITH ch_agg AS (
  SELECT
    call_time::date AS report_date,
    phone,
    count(*)                                                            AS attempts,
    count(*) FILTER (WHERE system_disposition='CONNECTED')              AS connected_calls,
    bool_or(system_disposition='CONNECTED')                            AS is_connected,
    bool_or(disposition_class='Interested')                            AS is_interested,
    bool_or(system_disposition='CONNECTED'
            AND EXTRACT(EPOCH FROM NULLIF(btrim(user_talk_time),'')::interval) > 30) AS is_successful,
    min(CASE WHEN campaign_name ILIKE '%ASR%' THEN 'Amritsar' ELSE 'Gurgaon' END)   AS location,
    sum(COALESCE(EXTRACT(EPOCH FROM NULLIF(btrim(user_talk_time),'')::interval),0))::bigint AS talk_secs
  FROM call_history
  WHERE phone IS NOT NULL AND btrim(phone) <> ''
  GROUP BY 1,2
),
-- leads deduped to ONE row per (date, phone); source = 'both' when loaded manual+prod same day
lu AS (
  SELECT report_date, phone,
    CASE WHEN bool_or(source='prod') AND bool_or(source='manual') THEN 'both'
         WHEN bool_or(source='prod') THEN 'prod' ELSE 'manual' END AS source
  FROM leads_unified
  WHERE phone IS NOT NULL AND btrim(phone) <> ''
  GROUP BY report_date, phone
)
SELECT
  lu.report_date,
  lu.source,
  COALESCE(ch.location, '(not dialed)')                              AS location,
  'Week-' || (FLOOR((EXTRACT(DAY FROM lu.report_date)
            + EXTRACT(ISODOW FROM date_trunc('month', lu.report_date)) - 2)/7)+1)::int::text AS week,
  'eulermotors' AS tenant_name, 'maxicus' AS entity_name,
  count(*)                                            AS leads_received,
  count(ch.phone)                                     AS leads_dialed,
  count(*) - count(ch.phone)                          AS leads_not_dialed,
  count(*) FILTER (WHERE ch.is_connected)             AS leads_connected,
  count(*) FILTER (WHERE ch.is_successful)            AS leads_successful,
  count(*) FILTER (WHERE ch.is_interested)            AS leads_interested,
  sum(COALESCE(ch.attempts,0))::bigint                AS lead_attempts,
  sum(COALESCE(ch.connected_calls,0))::bigint         AS lead_connected_calls,
  sum(COALESCE(ch.talk_secs,0))::bigint               AS lead_talk_secs
FROM lu
LEFT JOIN ch_agg ch ON ch.report_date = lu.report_date AND ch.phone = lu.phone
WHERE lu.report_date > '{last_processed}'
  AND lu.report_date <= '{high_water_mark}'
GROUP BY lu.report_date, lu.source, COALESCE(ch.location, '(not dialed)')

"""
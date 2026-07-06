

WITH ch AS (
  SELECT
    call_time::date                                                                AS report_date,
    campaign_name,
    CASE WHEN campaign_name ILIKE '%ASR%' THEN 'Amritsar' ELSE 'Gurgaon' END       AS location,

    system_disposition,
    COALESCE(NULLIF(disposition_class,''),'untagged')                              AS disposition_class,
    COALESCE(NULLIF(disposition_code ,''),'untagged')                              AS disposition_code,

    EXTRACT(EPOCH FROM NULLIF(user_talk_time,'')::interval)                        AS talk_sec

  FROM call_history
)

SELECT
  report_date,
  'Week-' || (FLOOR((EXTRACT(DAY FROM report_date)
            + EXTRACT(ISODOW FROM date_trunc('month', report_date)) - 2)/7)+1)::int::text AS week,

  campaign_name,
  location,

  system_disposition,
  disposition_class,
  disposition_code,

  'eulermotors'                                                       AS tenant_name,
  'maxicus'                                                           AS entity_name,

  count(*)                                                            AS dp_count,
  COALESCE(SUM(talk_sec),0)::bigint                                   AS dp_talk_secs

FROM ch

WHERE report_date > '{last_processed}'
  AND report_date <= '{high_water_mark}'

GROUP BY report_date, campaign_name, location, 
    system_disposition, disposition_class, disposition_code
 
 
-- ======================================================================
-- ======================================================================
-- ======================================================================
-- ======================================================================


DDL


CREATE TABLE IF NOT EXISTS eulermotors.euler_fact_disposition_report
(
  report_date                   Date,
  week                          String,
  campaign_name                 String,
  location                      String,
  system_disposition            String,
  disposition_class             String,
  disposition_code              String,
  tenant_name                   String,
  entity_name                   String,
  dp_count                      Int32,
  dp_talk_secs                  Int64
)
ENGINE = MergeTree()
ORDER BY (report_date, campaign_name, system_disposition, disposition_class, disposition_code)

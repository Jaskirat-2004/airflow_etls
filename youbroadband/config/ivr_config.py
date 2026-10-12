# JS =============================================================================================================== JS
#                                   QUERIES FOR IVR HUNGUP FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

YOUBROADBAND_FACT_IVR_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS youbroadband.youbroadband_fact_ivr_report
(
    report_date          Date,
    week                 String,
    tenant_name          String,
    entity_name          String,

    iv_total_calls       UInt32,
    iv_api1_hangup       UInt32,

    loaded_at            DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date)

"""
# JS ======================================= QUERY ======================================= JS

YOUBROADBAND_FACT_IVR_REPORT_QUERY = """

SELECT
    iv.report_date,
    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM iv.report_date)/7.0),4)::int AS week,
    'youbroadband'            AS tenant_name,
    'maxicus'                 AS entity_name,

    COUNT(*)                  AS iv_total_calls,

    SUM(CASE WHEN TRIM(COALESCE(iv.language_selection_input,'')) ~ '^[0-9]+$'
              AND NULLIF(TRIM(COALESCE(iv.api_1_response,'')),'')     IS NULL
              AND NULLIF(TRIM(COALESCE(iv.customer_type_menu,'')),'') IS NOT NULL
             THEN 1 ELSE 0 END) AS iv_api1_hangup

FROM ivr_footprint iv
WHERE iv.report_date >  DATE '{last_processed}'
  AND iv.report_date <= DATE '{high_water_mark}'
GROUP BY iv.report_date

"""
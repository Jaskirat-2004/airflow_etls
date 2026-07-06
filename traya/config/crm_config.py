# JS =============================================================================================================== JS
#                                       QUERIES FOR CRM REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS =======================================  DDL  ======================================= JS


TRAYA_FACT_CRM_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS traya.traya_fact_crm_report
(
    report_date                 Date,
    week                        String,
    tenant_name                 String,
    entity_name                 String,

    employee_id                 String,
    coach_name                  String,
    process                     String,
    location                    String,
    num_attempted               Int32,
    num_answered                Int32,
    num_unanswered              Int32,
    total_time_spent            Int32,
    talk_time                   Int32,
    calls_over_20m              Int32,
    miss_match_count            Int32,
    tl_name                     String,
    group_name                  String,
    sub_group                   String,
    operations_manager          String,
    line_of_business            String,
    gender                      String,
    designation                 String,
    batch_number                String,
    versant_score               String,
    education_level             String,
    active_status               String,
    tenure                      String,
    date_of_joining             String
    
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, employee_id)

"""

# JS ======================================= FACT TABLE ======================================= JS


TRAYA_FACT_CRM_REPORT_QUERY = """

SELECT
    c.report_date,

    -- CASE 
    --     WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 1 AND 7 THEN 'Week 1'
    --     WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 8 AND 14 THEN 'Week 2'
    --     WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 15 AND 21 THEN 'Week 3'
    --     WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 22 AND 28 THEN 'Week 4'
    --     WHEN EXTRACT(DAY FROM c.report_date) >= 29 THEN 'Week 5'
    -- END as week,

    'Week-' || (
    FLOOR(
        (EXTRACT(DAY FROM c.report_date) + 
        EXTRACT(ISODOW FROM date_trunc('month', c.report_date)) - 2) / 7
        ) + 1 )::int::text  AS week,

    c.employee_id,
    'traya' as tenant_name,
    'maxicus' as entity_name,

    COALESCE(c.coach_name, '')           AS coach_name,
    COALESCE(c.process, '')              AS process,
    COALESCE(c.location, '')             AS location,
    COALESCE(c.num_attempted, 0)         AS num_attempted,
    COALESCE(c.num_answered, 0)          AS num_answered,
    COALESCE(c.num_unanswered, 0)        AS num_unanswered,
    COALESCE(c.total_time_spent, 0)      AS total_time_spent,
    COALESCE(c.talk_time, 0)             AS talk_time,
    COALESCE(c.calls_over_20m, 0)        AS calls_over_20m,
    COALESCE(c.miss_match_count, 0)      AS miss_match_count,
    
    COALESCE(m.team_leader, '')               AS tl_name,
    COALESCE(m.group_name, 'UNKNOWN')         AS group_name,
    COALESCE(m.sub_group, 'UNKNOWN')          AS sub_group,
    COALESCE(m.operations_manager, 'UNKNOWN') AS operations_manager,   -- AM level (above TL)
    COALESCE(m.line_of_business, 'UNKNOWN')   AS line_of_business,
    COALESCE(m.gender, 'UNKNOWN')             AS gender,
    COALESCE(m.designation, 'UNKNOWN')        AS designation,
    COALESCE(m.batch_number, 'UNKNOWN')       AS batch_number,
    COALESCE(m.versant_score, 'UNKNOWN')      AS versant_score,
    COALESCE(m.education_level, 'UNKNOWN')    AS education_level,
    COALESCE(m.active_status, 'UNKNOWN')      AS active_status,
    COALESCE(m.tenure, 'UNKNOWN')             AS tenure,
    m.date_of_joining                         AS date_of_joining       -- for tenure buckets

FROM calling_kpis_data as c
LEFT JOIN master_tracker as m
    ON c.report_date = m.report_date 
    AND c.employee_id = m.emp_id
WHERE c.report_date > '{last_processed}'
    AND c.report_date <= '{high_water_mark}'

"""

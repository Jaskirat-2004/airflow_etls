
WITH ses AS (
    SELECT
        report_date,
        lower(trim(user_id)) AS agent_email,
        

        CASE
            WHEN trim(COALESCE(break_reason,'')) = ''                              THEN 'Not Specified'
            WHEN trim(break_reason) = 'erroneous.channel.system.initiated.break'   THEN 'System Break'
            ELSE trim(break_reason)
        END AS break_reason,

        COUNT(*)                                                                          AS segments,
        COUNT(DISTINCT session_id)                                                        AS sessions,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(break_duration),'')::interval),0))::bigint AS break_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(ready_duration),'')::interval),0))::bigint AS ready_secs
    
    FROM agent_session_details
    WHERE lower(user_id) LIKE '%maxicus%'
    AND report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1,2,3
    ),

mt AS (
    SELECT DISTINCT ON (report_date, lower(trim(official_email)))
        report_date                        AS report_date,
        lower(trim(official_email)) AS agent_email,
        emp_id                      AS mt_emp_id, 
        emp_name                    AS mt_emp_name, 
        designation                 AS mt_designation,
        team_leader                 AS mt_team_leader, 
        operations_manager          AS mt_operations_manager,
        group_name                  AS mt_group_name, 
        sub_group                   AS mt_sub_group, 
        line_of_business            AS mt_line_of_business,
        tenure                      AS mt_tenure,
        date_of_joining             AS mt_doj, 
        batch_number                AS mt_batch,
        versant_score               AS mt_versant, 
        active_status               AS mt_active_status, 
        gender                      AS mt_gender,
        education_level             AS mt_education, 
        fresher_experience          AS mt_fresher_exp,

        CASE
            WHEN group_name='Training' THEN 'Training' 
            WHEN group_name='OJT' THEN 'OJT' 
            ELSE 'Live' 
        END                         AS mt_status

    FROM master_tracker
    WHERE official_email IS NOT NULL AND official_email <> ''
    ORDER BY report_date, lower(trim(official_email)), emp_id
)

SELECT
    s.report_date, 
    s.agent_email, 
    'traya' as tenant_name,
    'maxicus' as entity_name,

    s.break_reason,
    mt.mt_emp_id, 
    mt.mt_emp_name, 
    mt.mt_designation, 
    mt.mt_status, 
    mt.mt_team_leader, 
    mt.mt_operations_manager,
    mt.mt_group_name, 
    mt.mt_sub_group, 
    mt.mt_line_of_business, 
    mt.mt_tenure, 
    mt.mt_doj, 
    mt.mt_batch,
    mt.mt_versant, 
    mt.mt_active_status, 
    mt.mt_gender, 
    mt.mt_education, 
    mt.mt_fresher_exp,
    s.segments, 
    s.sessions, 
    s.break_secs, 
    s.ready_secs

FROM ses s
    LEFT JOIN mt 
    ON mt.report_date = s.report_date AND mt.agent_email = s.agent_email;

-- ===============================================================================================
-- ===============================================================================================
-- ===============================================================================================
-- ===============================================================================================

Proposed DDL (ClickHouse)

CREATE TABLE IF NOT EXISTS traya.traya_fact_aux_report (
    report_date             Date, 
    agent_email             String, 
    break_reason            String,
    mt_emp_id               Nullable(String), 
    mt_emp_name             Nullable(String), 
    mt_designation          Nullable(String),
    mt_status               Nullable(String), 
    mt_team_leader          Nullable(String), 
    mt_operations_manager   Nullable(String),
    mt_group_name           Nullable(String), 
    mt_sub_group            Nullable(String), 
    mt_line_of_business     Nullable(String),
    mt_tenure               Nullable(String), 
    mt_doj                  Nullable(String), 
    mt_batch                Nullable(String),
    mt_versant              Nullable(String), 
    mt_active_status        Nullable(String), 
    mt_gender               Nullable(String),
    mt_education            Nullable(String), 
    mt_fresher_exp          Nullable(String),
    segments                Int32, 
    sessions                Int32, 
    break_secs              Int64, 
    ready_secs              Int64
) 
ENGINE = MergeTree() 
PARTITION BY toYYYYMM(report_date) 
ORDER BY (report_date, agent_email, break_reason)

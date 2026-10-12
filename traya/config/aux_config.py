# JS =============================================================================================================== JS
#                                       QUERIES FOR AUX REPORT FACT TABLE
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

TRAYA_FACT_AUX_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS traya.traya_fact_aux_report (
    report_date             Date, 
    agent_email             String,
    tenant_name             String,
    entity_name             String,

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

"""


# JS ======================================= FACT TABLE ======================================= JS


TRAYA_FACT_AUX_REPORT_QUERY = """

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
    )

SELECT
    s.report_date,
    s.agent_email,
    'traya' as tenant_name,
    'maxicus' as entity_name,

    s.break_reason,
    xw.emp_id                          AS mt_emp_id,
    mt.emp_name                        AS mt_emp_name,
    mt.designation                     AS mt_designation,

    CASE
        WHEN mt.emp_id IS NULL        THEN NULL
        WHEN mt.group_name='Training' THEN 'Training'
        WHEN mt.group_name='OJT'      THEN 'OJT'
        ELSE 'Live'
    END                                AS mt_status,

    mt.team_leader                     AS mt_team_leader,
    mt.operations_manager              AS mt_operations_manager,
    mt.group_name                      AS mt_group_name,
    mt.sub_group                       AS mt_sub_group,
    mt.line_of_business                AS mt_line_of_business,
    mt.tenure                          AS mt_tenure,
    mt.date_of_joining                 AS mt_doj,
    mt.batch_number                    AS mt_batch,
    mt.versant_score                   AS mt_versant,
    mt.active_status                   AS mt_active_status,
    mt.gender                          AS mt_gender,
    mt.education_level                 AS mt_education,
    mt.fresher_experience              AS mt_fresher_exp,
    s.segments,
    s.sessions,
    s.break_secs,
    s.ready_secs

FROM ses s

    LEFT JOIN agent_identity_map xw
           ON xw.client_id = s.agent_email
          AND s.report_date BETWEEN xw.valid_from AND xw.valid_to

    LEFT JOIN master_tracker mt
           ON mt.emp_id      = xw.emp_id
          AND mt.report_date = s.report_date;

"""



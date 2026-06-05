
SELECT
    c.report_date,

    CASE 
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 1 AND 7 THEN 'Week 1'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 8 AND 14 THEN 'Week 2'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 15 AND 21 THEN 'Week 3'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 22 AND 28 THEN 'Week 4'
        WHEN EXTRACT(DAY FROM c.report_date) >= 29 THEN 'Week 5'
    END as week,

    c.employee_id,
    COALESCE(c.coach_name, '')           AS coach_name,
    COALESCE(c.tl_name, '')              AS tl_name,
    COALESCE(c.process, '')              AS process,
    COALESCE(c.location, '')             AS location,
    COALESCE(c.num_attempted, 0)         AS num_attempted,
    COALESCE(c.num_answered, 0)          AS num_answered,
    COALESCE(c.num_unanswered, 0)        AS num_unanswered,
    COALESCE(c.total_time_spent, 0)      AS total_time_spent,
    COALESCE(c.talk_time, 0)             AS talk_time,
    COALESCE(c.calls_over_20m, 0)        AS calls_over_20m,
    COALESCE(c.miss_match_count, 0)      AS miss_match_count,
    
    COALESCE(m.group_name, 'UNKNOWN')    AS group_name,
    COALESCE(m.sub_group, 'UNKNOWN')     AS sub_group

FROM calling_kpis_data as c
LEFT JOIN master_tracker as m
    ON c.report_date = m.date 
    AND c.employee_id = m.emp_id
WHERE c.report_date > '{last_processed}'
    AND c.report_date <= '{high_water_mark}'


-- ##############################################################################
-- ##############################################################################
-- ##############################################################################

SELECT
    c.report_date,

    CASE 
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 1 AND 7 THEN 'Week 1'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 8 AND 14 THEN 'Week 2'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 15 AND 21 THEN 'Week 3'
        WHEN EXTRACT(DAY FROM c.report_date) BETWEEN 22 AND 28 THEN 'Week 4'
        WHEN EXTRACT(DAY FROM c.report_date) >= 29 THEN 'Week 5'
    END as week,

    c.employee_id,
    c.coach_name,
    c.tl_name,
    c.process,
    c.location,
    c.num_attempted,
    c.num_answered,
    c.num_unanswered,
    c.total_time_spent,
    c.talk_time,
    c.calls_over_20m,
    c.miss_match_count,

    m.group_name,
    m.sub_group

FROM calling_kpis_data as c
LEFT JOIN master_tracker as m
    ON c.report_date = m.date 
    AND c.employee_id = m.emp_id ;



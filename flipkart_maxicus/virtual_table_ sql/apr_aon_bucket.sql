
SELECT
    f.*,
    -- AON — age on network in days, as of TODAY. NULL where the agent has no production date.
    if(isNull(f.mp_production_date),
       NULL,
       dateDiff('day', f.mp_production_date, today()))                        AS aon_days,

    multiIf(
        isNull(f.mp_production_date),                                  '<0 (OJT)',
        dateDiff('day', f.mp_production_date, today()) <  0,           '<0 (OJT)',
        dateDiff('day', f.mp_production_date, today()) <= 30,          '0-30',
        dateDiff('day', f.mp_production_date, today()) <= 60,          '30-60',
        dateDiff('day', f.mp_production_date, today()) <= 90,          '60-90',
                                                                       '90+'
    )                                                                         AS aon_bucket,

    if(f.mp_status_internal = 'Production'
       AND isNotNull(f.mp_production_date)
       AND f.report_date >= f.mp_production_date,
       'Production',
       'OJT')                                                                 AS department_name,

    multiIf(
        f.mp_status_internal = 'Production'
            AND isNotNull(f.mp_production_date)
            AND f.report_date >= f.mp_production_date,                        'Production',
        isNull(f.mp_ojt_start_date),                                          'Unknown',
        concat('Day-', toString(dateDiff('day', f.mp_ojt_start_date, today())))
    )                                                                         AS ojt_day,


    if(f.mp_designation = 'Executive', 'Agent', 'Support')                    AS agent_type

FROM flipkart_maxicus.flipkart_fact_apr_report AS f

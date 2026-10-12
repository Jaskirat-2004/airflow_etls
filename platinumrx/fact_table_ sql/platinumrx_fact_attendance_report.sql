
-- PLATINUMRX FACT ATTENDANCE REPORT
-- readable mirror of PLATINUMRX_FACT_ATTENDANCE_REPORT_QUERY in config/attendance_config.py
-- braces are DOUBLED because the string is run through python .format(last_processed=..., high_water_mark=...)
-- design + reasoning : platinumrx/05-wfm-report.md

WITH
ros AS (
    SELECT
        report_date,
        emp_id::text AS emp_id,
        roster AS shift_raw,

        substring(roster from '^([0-9]{{1,2}}:[0-9]{{2}})')        AS shift_start,
        substring(roster from '([0-9]{{1,2}}:[0-9]{{2}})$')        AS shift_end,
        substring(roster from '^([0-9]{{1,2}}:[0-9]{{2}})')::time  AS ss,
        substring(roster from '([0-9]{{1,2}}:[0-9]{{2}})$')::time  AS se,

        CASE
            WHEN roster ~ '^[0-9]{{1,2}}:[0-9]{{2}}'      THEN 'SHIFT'
            WHEN upper(trim(roster)) = 'WO'                THEN 'WO'
            WHEN upper(trim(roster)) = 'PL'                THEN 'PL'
            WHEN upper(trim(roster)) = 'LEAVE'             THEN 'Leave'
            WHEN upper(trim(roster)) = 'HD'                THEN 'HD'
            ELSE 'NO-ROSTER'
        END AS status

    FROM platinumrx_roster
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
),

-- the uploaded login table. MIN/MAX is a no-op if it is already agent-day grain
ses AS (
    SELECT
        report_date,
        emp_id::text AS emp_id,
        MIN(first_login) AS first_login,
        MAX(last_logout) AS last_logout
    FROM platinumrx_agent_login
    WHERE report_date > '{last_processed}' AND report_date <= '{high_water_mark}'
    GROUP BY 1,2
),

-- HEAD COUNT is the spine : every agent-day in the fact comes from here
base AS (
    SELECT
        h.report_date,
        h.employee_id::text AS emp_id,
        h.employee_name AS emp_name,
        h.designation_name AS designation,
        h.grade,
        h.employee_type,
        h.reporting_to_name AS team_leader,
        h.functional_reporting_to_name AS functional_manager,
        h.location_name AS location,
        h.ou_name,
        h.department_name AS department,
        h.batch_number AS batch,
        h.gender,
        h.current_status,
        h.workplace_category AS wfo_wfh,
        h.date_of_joining AS doj,
        GREATEST((h.report_date - h.date_of_joining), 0) AS tenure_days,

        COALESCE(r.status,'NO-ROSTER') AS roster_status,
        r.shift_raw, r.shift_start, r.shift_end, r.ss, r.se,
        CASE WHEN r.se IS NOT NULL THEN EXTRACT(EPOCH FROM (r.se - r.ss))::int ELSE 0 END AS scheduled_secs,

        s.first_login,
        s.last_logout,
        (s.last_logout IS NOT NULL AND s.first_login IS NOT NULL)::int AS has_session,

        -- login window = logout - login (GROSS : breaks are included, see 05-wfm-report.md section A)
        CASE WHEN s.first_login IS NOT NULL AND s.last_logout IS NOT NULL
             THEN GREATEST(EXTRACT(EPOCH FROM (s.last_logout - s.first_login))::int, 0) ELSE 0 END AS login_secs,

        0 AS break_secs,        -- placeholder : set from the status-event dump when break lands
        0 AS exception_secs     -- placeholder : no downtime/exception feed for PLATINUMRX

    FROM platinumrx_head_count h
    LEFT JOIN ros r ON r.report_date = h.report_date AND r.emp_id = h.employee_id::text
    LEFT JOIN ses s ON s.report_date = h.report_date AND s.emp_id = h.employee_id::text
    WHERE h.report_date > '{last_processed}' AND h.report_date <= '{high_water_mark}'
      AND h.employee_type = 'Agent'
      AND h.current_status = 'Active'
)

SELECT
    report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM report_date)/7.0)::int              AS week,
    emp_id,
    emp_name,
    'platinumrx' AS tenant_name,
    'maxicus'    AS entity_name,
    COALESCE(ou_name,'PlatinumX')                                        AS process,
    CASE WHEN ou_name ILIKE '%Sales%' THEN 'Sales' ELSE 'Support' END    AS lob,

    designation, grade, employee_type, team_leader, functional_manager,
    location, ou_name, department, batch, gender, current_status, wfo_wfh, doj, tenure_days,

    CASE WHEN tenure_days<=30 THEN '0-30'
         WHEN tenure_days<=60 THEN '31-60'
         WHEN tenure_days<=90 THEN '61-90'
         ELSE '>90' END                                                  AS tenure_bucket,

    shift_raw, roster_status, shift_start, shift_end, scheduled_secs,
    first_login, last_logout,
    login_secs, break_secs, exception_secs,
    GREATEST(login_secs - break_secs, 0) + exception_secs                AS adjusted_login_secs,
    has_session,
    1 AS hc_flag,

    -- roster denominator : rostered days only, WO and NO-ROSTER excluded (house rule)
    (CASE WHEN roster_status IN ('SHIFT','HD','PL','Leave') THEN 1 ELSE 0 END)::numeric AS roster_denom,

    -- SHRINKAGE attendance (Present >= 7:30 / HD >= 4:00 on adjusted_login_secs)
    CASE WHEN roster_status IN ('WO','NO-ROSTER')                                          THEN 'Week-Off'
         WHEN roster_status='PL'                                                           THEN 'Planned-Leave'
         WHEN roster_status='Leave'                                                        THEN 'Leave'
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000 THEN 'Present'
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=14400 THEN 'Half-Day'
         WHEN roster_status IN ('SHIFT','HD')                                              THEN 'Absent'
         ELSE 'No-Roster' END                                            AS shrink_attendance,

    CASE WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=14400 THEN 0.5
         ELSE 0 END                                                      AS shr_present_equiv,

    -- PL = roster-scheduled leave, UPL = Absent on a rostered day (HD-short = 0.5)
    CASE WHEN roster_status IN ('PL','Leave') THEN 1.0 ELSE 0 END         AS shr_planned,

    CASE WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs<14400 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs<27000 THEN 0.5
         ELSE 0 END                                                      AS shr_unplanned,

    -- PAYROLL attendance (8:00 / 4:30)
    CASE WHEN roster_status IN ('WO','NO-ROSTER')                                          THEN 'Week-Off'
         WHEN roster_status='PL'                                                           THEN 'Planned-Leave'
         WHEN roster_status='Leave'                                                        THEN 'Leave'
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=28800 THEN 'Present'
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=16200 THEN 'Half-Day'
         WHEN roster_status IN ('SHIFT','HD')                                              THEN 'Absent'
         ELSE 'No-Roster' END                                            AS payroll_attendance,

    CASE WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=28800 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs>=16200 THEN 0.5
         ELSE 0 END                                                      AS pay_present_equiv,

    CASE WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs<16200 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND GREATEST(login_secs-break_secs,0)+exception_secs<28800 THEN 0.5
         ELSE 0 END                                                      AS pay_unplanned,

    -- SHIFT ADHERENCE : denominator = rostered SHIFT day, present, with a session
    (CASE WHEN roster_status='SHIFT' AND has_session=1
               AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000 THEN 1 ELSE 0 END) AS adh_denom,

    -- PLATINUMRX Glossary window : [shift_start - 30m, shift_start + 15m]
    (CASE WHEN roster_status='SHIFT' AND has_session=1
               AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000
               AND first_login::time BETWEEN ss - interval '30 min' AND ss + interval '15 min'
          THEN 1 ELSE 0 END)                                             AS login_adherent,

    (CASE WHEN roster_status='SHIFT' AND has_session=1
               AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000
               AND last_logout::time >= se - interval '15 min' THEN 1 ELSE 0 END) AS logout_adherent,

    (CASE WHEN roster_status='SHIFT' AND has_session=1
               AND GREATEST(login_secs-break_secs,0)+exception_secs>=27000
               AND first_login::time BETWEEN ss - interval '30 min' AND ss + interval '15 min'
               AND last_logout::time >= se - interval '15 min' THEN 1 ELSE 0 END) AS day_adherent,

    -- signed : >0 = late login, <0 = early login. Makes the grace tunable in-dashboard
    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND first_login IS NOT NULL
               THEN EXTRACT(EPOCH FROM (first_login::time - ss))::int ELSE 0 END) AS delay_login_secs,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND last_logout IS NOT NULL
               THEN EXTRACT(EPOCH FROM (se - last_logout::time))::int ELSE 0 END) AS early_logout_secs,

    -- FTE : 8h cap per the PLATINUMRX FTE report
    LEAST(GREATEST(login_secs - break_secs, 0), 28800)                   AS fte_capped_secs

FROM base

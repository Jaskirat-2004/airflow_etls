
WITH
ros AS (
    SELECT 
        report_date, 
        emp_id, 
        roster AS shift_raw,

        substring(roster from '^([0-9]{{2}}:[0-9]{{2}})')        AS shift_start,
        substring(roster from '([0-9]{{2}}:[0-9]{{2}})$')        AS shift_end,
        substring(roster from '^([0-9]{{2}}:[0-9]{{2}})')::time  AS ss,
        substring(roster from '([0-9]{{2}}:[0-9]{{2}})$')::time  AS se,
        
        CASE 
            WHEN roster ~ '^[0-9]{{2}}:[0-9]{{2}}' THEN 'SHIFT'
            WHEN upper(roster)='WO' THEN 'WO' 
            WHEN roster='Leave' THEN 'Leave' 
            ELSE upper(roster) 
        END AS status
    
    FROM roster
    WHERE report_date > '{last_processed}'
),

ap_iv AS (
    SELECT 
        report_date, 
        split_part(user_id,'@',1) AS emp_id, 
        interval_start::time AS iv,
        EXTRACT(EPOCH FROM NULLIF(total_ready_duration,'')::interval)::int AS rs,
        EXTRACT(EPOCH FROM NULLIF(total_break_duration,'')::interval)::int AS bs
    
    FROM agent_productivity_interval_summary
    WHERE report_date > '{last_processed}'
),

ap AS (
    SELECT 
        a.report_date, 
        a.emp_id,
        SUM(a.rs) AS raw_ready, 
        SUM(a.bs) AS break_secs,
        SUM(CASE WHEN r.ss IS NULL THEN a.rs WHEN a.iv>=r.ss AND a.iv<r.se THEN a.rs ELSE 0 END) AS inshift_ready,
        SUM(CASE WHEN r.ss IS NULL THEN a.rs WHEN a.iv>=r.ss-interval '30 min' AND a.iv<r.se+interval '30 min' THEN a.rs ELSE 0 END) AS inshift_ready_buf
    FROM ap_iv a
    LEFT JOIN ros r ON r.report_date=a.report_date AND r.emp_id=a.emp_id
    GROUP BY 1,2
),

ap_camp AS (   -- primary campaign/process = max-ready campaign that day (drives call_type + campaign filter)
    SELECT DISTINCT ON (report_date, emp_id) report_date, emp_id, campaign_name AS primary_campaign, process_name AS primary_process
    FROM (SELECT report_date, split_part(user_id,'@',1) AS emp_id, campaign_name, process_name,
                 SUM(EXTRACT(EPOCH FROM NULLIF(total_ready_duration,'')::interval)) rd
          FROM agent_productivity_interval_summary WHERE report_date > '{last_processed}' GROUP BY 1,2,3,4) t
    ORDER BY report_date, emp_id, rd DESC NULLS LAST
),

ses AS (
    SELECT 
    report_date, 
    split_part(user_id,'@',1) AS emp_id, 
    MIN(login_time) AS first_login, 
    MAX(logout_time) AS last_logout
    
    FROM agent_session_details
    WHERE report_date > '{last_processed}'
    GROUP BY 1,2
),

dt AS (
    SELECT 
        report_date, 
        emp_id,
        SUM(CASE WHEN exception_hr ~ ':' THEN EXTRACT(EPOCH FROM NULLIF(exception_hr,'')::interval)
                 WHEN exception_hr ~ '^[0-9.]+$' AND exception_hr::numeric <= 1 THEN exception_hr::numeric*86400
                 WHEN exception_hr ~ '^[0-9.]+$' THEN exception_hr::numeric*3600 ELSE 0 END)::int AS exception_secs
    FROM downtime_login_hr
    WHERE report_date > '{last_processed}'
    GROUP BY 1,2
),

base AS (
    SELECT
        h.report_date, 
        h.employee_id AS emp_id, 
        h.employee_name AS emp_name,
        h.designation_name AS designation, 
        h.grade,
        h.employee_type,
        h.reporting_to_name AS team_leader, 
        h.functional_reporting_to_name AS functional_manager,
        h.location_name AS location, 
        h.ou_name, 
        h.department_name AS department,
        h.gender, 
        h.current_status, 
        h.workplace_category AS wfo_wfh, 
        h.date_of_joining AS doj,
        GREATEST((h.report_date - h.date_of_joining), 0) AS tenure_days,
        COALESCE(r.status,'NO-ROSTER') AS roster_status, 
        r.shift_raw, 
        r.shift_start, 
        r.shift_end, 
        r.ss, 
        r.se,
        CASE WHEN r.se IS NOT NULL THEN EXTRACT(EPOCH FROM (r.se - r.ss))::int ELSE 0 END AS scheduled_secs,
        
        s.first_login, 
        s.last_logout,
         (s.last_logout IS NOT NULL)::int AS has_session,
        
        COALESCE(ap.raw_ready,0) AS raw_ready_secs, 
        COALESCE(ap.break_secs,0) AS break_secs,
        COALESCE(ap.inshift_ready,0) AS inshift_ready_secs, 
        COALESCE(ap.inshift_ready_buf,0) AS inshift_ready_buf_secs,
        COALESCE(dt.exception_secs,0) AS exception_secs,
        (COALESCE(ap.raw_ready,0) + COALESCE(dt.exception_secs,0)) AS adjusted_ready_secs,
        ac.primary_campaign, 
        ac.primary_process
    
    FROM vodafone_head_count h
    
    LEFT JOIN ros r      
        ON r.report_date  = h.report_date AND r.emp_id  = h.employee_id
    LEFT JOIN ap         
        ON ap.report_date = h.report_date AND ap.emp_id = h.employee_id
    LEFT JOIN ap_camp ac 
        ON ac.report_date = h.report_date AND ac.emp_id = h.employee_id
    LEFT JOIN ses s      
        ON s.report_date  = h.report_date AND s.emp_id  = h.employee_id
    LEFT JOIN dt         
        ON dt.report_date = h.report_date AND dt.emp_id = h.employee_id
    
    WHERE h.report_date > '{last_processed}'
)
SELECT
    report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM report_date)/7.0)::int          AS week,
    emp_id, 
    emp_name, 
    'vodafone' AS tenant_name, 
    'maxicus' AS entity_name,
    COALESCE(ou_name,'Vodafone') AS process, 
    primary_campaign,
    
    CASE WHEN primary_campaign = 'Chat_In' THEN 'Inbound' WHEN primary_campaign IS NULL THEN NULL ELSE 'Outbound' END AS call_type,
    
    designation, 
    grade, 
    employee_type, 
    team_leader, 
    functional_manager, 
    location, 
    ou_name, 
    department,
    gender, 
    current_status, 
    wfo_wfh, 
    doj, 
    tenure_days,
    
    CASE WHEN tenure_days<=30 THEN '0-30' WHEN tenure_days<=60 THEN '31-60' WHEN tenure_days<=90 THEN '61-90' ELSE '>90' END AS tenure_bucket,
    
    shift_raw, 
    roster_status, 
    shift_start, 
    shift_end, 
    scheduled_secs,
    first_login, 
    last_logout,
    CASE WHEN has_session=1 THEN GREATEST(EXTRACT(EPOCH FROM (last_logout-first_login))::int,0) ELSE 0 END AS login_window_secs,
    raw_ready_secs, 
    break_secs, 
    exception_secs, 
    adjusted_ready_secs, 
    inshift_ready_secs, 
    inshift_ready_buf_secs,
    has_session, 1 AS hc_flag,

    (CASE WHEN roster_status IN ('SHIFT','HD','PL','Leave') THEN 1 ELSE 0 END)::numeric AS roster_denom,

    -- SHRINKAGE (Present>=7:30 / HD>=4:00 on adjusted_ready); HD = 0.5 unplanned
    CASE WHEN roster_status IN ('WO','OFF ROSTER') THEN 'Week-Off' WHEN roster_status='PL' THEN 'Planned-Leave'
         WHEN roster_status='Leave' THEN 'Leave'
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=27000 THEN 'Present'
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=14400 THEN 'Half-Day'
         WHEN roster_status IN ('SHIFT','HD') THEN 'Absent' ELSE 'No-Roster' END AS shrink_attendance,

    CASE WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=27000 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=14400 THEN 0.5 ELSE 0 END AS shr_present_equiv,

    CASE WHEN roster_status='PL' THEN 1.0 ELSE 0 END AS shr_planned,

    CASE WHEN roster_status='Leave' THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs<14400 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs<27000 THEN 0.5 ELSE 0 END AS shr_unplanned,

    -- PAYROLL (Present>=8:00 / HD>=4:30)
    CASE WHEN roster_status IN ('WO','OFF ROSTER') THEN 'Week-Off' WHEN roster_status='PL' THEN 'Planned-Leave'
         WHEN roster_status='Leave' THEN 'Leave'
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=28800 THEN 'Present'
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=16200 THEN 'Half-Day'
         WHEN roster_status IN ('SHIFT','HD') THEN 'Absent' ELSE 'No-Roster' END AS payroll_attendance,

    CASE WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=28800 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs>=16200 THEN 0.5 ELSE 0 END AS pay_present_equiv,

    CASE WHEN roster_status='Leave' THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs<16200 THEN 1.0
         WHEN roster_status IN ('SHIFT','HD') AND adjusted_ready_secs<28800 THEN 0.5 ELSE 0 END AS pay_unplanned,

    -- SHIFT ADHERENCE (login +/-15 window drives SA%; logout + combined added Euler-style; signed secs stored, tunable)
    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND adjusted_ready_secs>=27000 THEN 1 ELSE 0 END) AS adh_denom,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND adjusted_ready_secs>=27000
               AND first_login::time BETWEEN ss - interval '15 min' AND ss + interval '15 min' THEN 1 ELSE 0 END) AS login_adherent,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND adjusted_ready_secs>=27000
               AND last_logout::time >= se - interval '15 min' THEN 1 ELSE 0 END) AS logout_adherent,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND adjusted_ready_secs>=27000
               AND first_login::time BETWEEN ss - interval '15 min' AND ss + interval '15 min'
               AND last_logout::time >= se - interval '15 min' THEN 1 ELSE 0 END) AS day_adherent,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND first_login IS NOT NULL
               THEN EXTRACT(EPOCH FROM (first_login::time - ss))::int ELSE 0 END) AS delay_login_secs,

    (CASE WHEN roster_status='SHIFT' AND has_session=1 AND last_logout IS NOT NULL
               THEN EXTRACT(EPOCH FROM (se - last_logout::time))::int ELSE 0 END) AS early_logout_secs

FROM base

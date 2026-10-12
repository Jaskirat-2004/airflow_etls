
# JS =============================================================================================================== JS
#                            QUERIES FOR ATTENDANCE FACT TABLE  (the WFM spine)
# JS =============================================================================================================== JS


# JS ======================================= DDL ======================================= JS

YOUBROADBAND_FACT_ATTENDANCE_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS youbroadband.youbroadband_fact_attendance_report
(
    report_date              Date,
    week                     String,
    tenant_name              String,
    entity_name              String,
    emp_id                   String,

    hc_emp_name              String,
    hc_designation           String,
    hc_grade                 String,
    hc_tl_name               String,
    hc_department            String,
    hc_current_status        String,
    shift_type               String,
    hc_flag                  UInt8,

    ros_shift_raw            String,
    ros_status               String,             -- SHIFT / HD / WO / PL / EXIT / NO-ROSTER
    ros_shift_start          String,             -- 'HH:MM', '' when not a shift row
    ros_shift_end            String,
    ros_scheduled_secs       Int32,
    roster_denom             Float64,            -- 1 on SHIFT / HD / PL, else 0

    ses_first_login          Nullable(DateTime),
    ses_last_logout          Nullable(DateTime),
    login_window_secs        Int32,
    ses_has_session          UInt8,

    ap_ready_secs            Int32,
    ap_break_secs            Int32,
    exception_secs           Int32,
    adjusted_ready_secs      Int32,
    billable_secs            Int32,

    shrink_attendance        String,
    shr_present_equiv        Float64,
    shr_planned              Float64,
    shr_unplanned            Float64,
    shr_hd                   Float64,            -- 1 on a Half-Day, so HD stays countable
    ros_wo                   UInt8,              -- 1 on a Week-Off; headcount = roster_denom + ros_wo

    payroll_attendance       String,
    pay_present_equiv        Float64,
    pay_unplanned            Float64,
    pay_hd                   Float64,

    delay_login_secs         Int32,              -- SIGNED: first_login - shift_start
    early_logout_secs        Int32,              -- SIGNED: shift_end - last_logout
    adh_denom                UInt8,
    adherent_first_login     UInt8,
    adherent_last_logout     UInt8,

    fte_target               UInt16,
    billing_days_target      UInt16,
    rate_per_fte             UInt32,

    loaded_at                DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, emp_id)

"""

# JS ======================================= QUERY ======================================= JS


YOUBROADBAND_FACT_ATTENDANCE_REPORT_QUERY = """

WITH ap_iv AS (
    SELECT
        TRIM(ap.user_id)   AS emp_id,
        ap.interval_start  AS ts,
        EXTRACT(EPOCH FROM NULLIF(TRIM(ap.total_ready_duration),'')::interval) AS s_ready,
        EXTRACT(EPOCH FROM NULLIF(TRIM(ap.total_break_duration),'')::interval) AS s_break,
        CASE WHEN LAG(ap.interval_start) OVER w IS NULL
                  OR ap.interval_start - LAG(ap.interval_start) OVER w > INTERVAL '3 hours'
             THEN 1 ELSE 0 END AS new_shift
    FROM agent_productivity_interval_summary ap
    WHERE ap.interval_start >= DATE '{last_processed}'
    WINDOW w AS (PARTITION BY TRIM(ap.user_id) ORDER BY ap.interval_start)
),

ap_shift AS (
    SELECT i.*, SUM(i.new_shift) OVER (PARTITION BY i.emp_id ORDER BY i.ts) AS shift_no
    FROM ap_iv i
),

ap_per_shift AS (
    SELECT emp_id, shift_no, MIN(ts)::date AS biz_date,
           COALESCE(SUM(s_ready),0)::int AS ap_ready_secs,
           COALESCE(SUM(s_break),0)::int AS ap_break_secs
    FROM ap_shift GROUP BY 1,2
),

ap AS (
    SELECT emp_id, biz_date,
           SUM(ap_ready_secs)::int AS ap_ready_secs,
           SUM(ap_break_secs)::int AS ap_break_secs
    FROM ap_per_shift GROUP BY 1,2
),

ses_iv AS (
    SELECT TRIM(s.user_id) AS emp_id, s.login_time, s.logout_time,
        CASE WHEN LAG(s.login_time) OVER v IS NULL
                  OR s.login_time - LAG(s.login_time) OVER v > INTERVAL '3 hours'
             THEN 1 ELSE 0 END AS new_shift
    FROM agent_session_details s
    WHERE s.login_time >= DATE '{last_processed}'
    WINDOW v AS (PARTITION BY TRIM(s.user_id) ORDER BY s.login_time)
),

ses_shift AS (
    SELECT x.*, SUM(x.new_shift) OVER (PARTITION BY x.emp_id ORDER BY x.login_time) AS shift_no
    FROM ses_iv x
),

ses_per_shift AS (
    SELECT emp_id, shift_no, MIN(login_time)::date AS biz_date,
           MIN(login_time) AS ses_first_login, MAX(logout_time) AS ses_last_logout
    FROM ses_shift GROUP BY 1,2
),

ses AS (
    SELECT emp_id, biz_date,
           MIN(ses_first_login) AS ses_first_login,
           MAX(ses_last_logout) AS ses_last_logout
    FROM ses_per_shift GROUP BY 1,2
),

-- roster: ONE text column holding either 'HH:MM - HH:MM' or a status code (Traya's shape)
ros AS (
    SELECT
        r.report_date,
        TRIM(r.emp_id)                                                        AS emp_id,
        COALESCE(NULLIF(TRIM(r.roster),''),'')                                AS ros_shift_raw,
        CASE WHEN TRIM(r.roster) ~ '^[0-9]{{2}}:[0-9]{{2}}' THEN 'SHIFT'
             ELSE UPPER(COALESCE(NULLIF(TRIM(r.roster),''),'NO-ROSTER')) END  AS ros_status,
        
        CASE WHEN TRIM(r.roster) ~ '^[0-9]{{2}}:[0-9]{{2}}'
             THEN TRIM(split_part(TRIM(r.roster),'-',1)) ELSE '' END          AS ros_shift_start,
        CASE WHEN TRIM(r.roster) ~ '^[0-9]{{2}}:[0-9]{{2}}'
             THEN TRIM(split_part(TRIM(r.roster),'-',2)) ELSE '' END          AS ros_shift_end
             
    FROM roster r
    WHERE r.report_date >  DATE '{last_processed}'
),

-- night shifts: if end <= start the shift crosses midnight, so end is on report_date + 1
ros_ts AS (
    SELECT
        ros.*,
        CASE WHEN ros_shift_start <> '' THEN ros.report_date + ros_shift_start::time END AS ss_ts,
        CASE WHEN ros_shift_end <> ''
             THEN CASE WHEN ros_shift_end::time <= ros_shift_start::time
                       THEN ros.report_date + 1 + ros_shift_end::time
                       ELSE ros.report_date     + ros_shift_end::time END END            AS se_ts
    FROM ros
),

base AS (
    SELECT
        hc.report_date,
        TRIM(hc.employee_id)                                     AS emp_id,
        COALESCE(NULLIF(TRIM(hc.employee_name),''),'NA')          AS hc_emp_name,
        COALESCE(NULLIF(TRIM(hc.designation_name),''),'NA')       AS hc_designation,
        COALESCE(NULLIF(TRIM(hc.grade),''),'NA')                 AS hc_grade,
        COALESCE(NULLIF(TRIM(hc.reporting_to_name),''),'NA')      AS hc_tl_name,
        COALESCE(NULLIF(TRIM(hc.department_name),''),'NA')        AS hc_department,
        COALESCE(NULLIF(TRIM(hc.current_status),''),'NA')         AS hc_current_status,
        CASE WHEN TRIM(hc.job_category) = 'Parttime' THEN '4FT' ELSE '9FT' END AS shift_type,

        COALESCE(r.ros_shift_raw,'')            AS ros_shift_raw,
        COALESCE(r.ros_status,'NO-ROSTER')      AS ros_status,
        COALESCE(r.ros_shift_start,'')          AS ros_shift_start,
        COALESCE(r.ros_shift_end,'')            AS ros_shift_end,
        r.ss_ts, r.se_ts,

        ses.ses_first_login, ses.ses_last_logout,
        COALESCE(ap.ap_ready_secs,0)            AS ap_ready_secs,
        COALESCE(ap.ap_break_secs,0)            AS ap_break_secs,
        0                                       AS exception_secs,
        COALESCE(ap.ap_ready_secs,0) + 0        AS adjusted_ready_secs
    FROM head_count hc
    LEFT JOIN ap     ON ap.biz_date  = hc.report_date AND ap.emp_id  = TRIM(hc.employee_id)
    LEFT JOIN ses    ON ses.biz_date = hc.report_date AND ses.emp_id = TRIM(hc.employee_id)
    LEFT JOIN ros_ts r ON r.report_date = hc.report_date AND r.emp_id = TRIM(hc.employee_id)
    WHERE hc.report_date >  DATE '{last_processed}'
)

SELECT
    b.report_date,
    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM b.report_date)/7.0),4)::int AS week,
    'youbroadband' AS tenant_name,
    'maxicus'      AS entity_name,
    b.emp_id,

    b.hc_emp_name, b.hc_designation, b.hc_grade, b.hc_tl_name,
    b.hc_department, b.hc_current_status, b.shift_type,
    1 AS hc_flag,

    b.ros_shift_raw, b.ros_status, b.ros_shift_start, b.ros_shift_end,
    CASE WHEN b.ss_ts IS NOT NULL AND b.se_ts IS NOT NULL
         THEN GREATEST(EXTRACT(EPOCH FROM (b.se_ts - b.ss_ts))::int,0) ELSE 0 END AS ros_scheduled_secs,
    (CASE WHEN b.ros_status IN ('SHIFT','HD','PL') THEN 1 ELSE 0 END)::numeric    AS roster_denom,

    b.ses_first_login, b.ses_last_logout,
    CASE WHEN b.ses_first_login IS NOT NULL AND b.ses_last_logout IS NOT NULL
         THEN GREATEST(EXTRACT(EPOCH FROM (b.ses_last_logout - b.ses_first_login))::int,0)
         ELSE 0 END                                                              AS login_window_secs,
    CASE WHEN b.ses_first_login IS NOT NULL AND b.ses_last_logout IS NOT NULL
         THEN 1 ELSE 0 END                                                       AS ses_has_session,

    b.ap_ready_secs, b.ap_break_secs, b.exception_secs, b.adjusted_ready_secs,
    LEAST(b.adjusted_ready_secs, 28800)                                          AS billable_secs,

    -- SHRINKAGE verdict: roster codes short-circuit, then 27000 / 14400
    CASE WHEN b.ros_status = 'WO'         THEN 'Week-Off'
         WHEN b.ros_status = 'EXIT'       THEN 'Exit'
         WHEN b.ros_status = 'PL'         THEN 'Planned-Leave'
         WHEN b.ros_status = 'NO-ROSTER'  THEN 'No-Roster'
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 27000 THEN 'Present'
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 14400 THEN 'Half-Day'
         WHEN b.ros_status IN ('SHIFT','HD') THEN 'Absent'
         ELSE 'Other' END                                                        AS shrink_attendance,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 27000 THEN 1.0
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 14400 THEN 0.5
         ELSE 0 END                                                              AS shr_present_equiv,
    CASE WHEN b.ros_status = 'PL' THEN 1.0 ELSE 0 END                            AS shr_planned,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs < 14400 THEN 1.0
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs < 27000 THEN 0.5
         ELSE 0 END                                                              AS shr_unplanned,
    CASE WHEN b.ros_status IN ('SHIFT','HD')
              AND b.adjusted_ready_secs >= 14400 AND b.adjusted_ready_secs < 27000
         THEN 1.0 ELSE 0 END                                                     AS shr_hd,
    CASE WHEN b.ros_status = 'WO' THEN 1 ELSE 0 END                              AS ros_wo,

    -- PAYROLL verdict: same shape, 28800 / 16200
    CASE WHEN b.ros_status = 'WO'        THEN 'Week-Off'
         WHEN b.ros_status = 'EXIT'      THEN 'Exit'
         WHEN b.ros_status = 'PL'        THEN 'Planned-Leave'
         WHEN b.ros_status = 'NO-ROSTER' THEN 'No-Roster'
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 28800 THEN 'Present'
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 16200 THEN 'Half-Day'
         WHEN b.ros_status IN ('SHIFT','HD') THEN 'Absent'
         ELSE 'Other' END                                                        AS payroll_attendance,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 28800 THEN 1.0
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs >= 16200 THEN 0.5
         ELSE 0 END                                                              AS pay_present_equiv,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs < 16200 THEN 1.0
         WHEN b.ros_status IN ('SHIFT','HD') AND b.adjusted_ready_secs < 28800 THEN 0.5
         ELSE 0 END                                                              AS pay_unplanned,
    CASE WHEN b.ros_status IN ('SHIFT','HD')
              AND b.adjusted_ready_secs >= 16200 AND b.adjusted_ready_secs < 28800
         THEN 1.0 ELSE 0 END                                                     AS pay_hd,

    -- ADHERENCE: signed deltas + the +/-15 min verdicts
    CASE WHEN b.ss_ts IS NOT NULL AND b.ses_first_login IS NOT NULL
         THEN EXTRACT(EPOCH FROM (b.ses_first_login - b.ss_ts))::int ELSE 0 END   AS delay_login_secs,
    CASE WHEN b.se_ts IS NOT NULL AND b.ses_last_logout IS NOT NULL
         THEN EXTRACT(EPOCH FROM (b.se_ts - b.ses_last_logout))::int ELSE 0 END   AS early_logout_secs,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.ses_first_login IS NOT NULL
              AND b.ss_ts IS NOT NULL THEN 1 ELSE 0 END                          AS adh_denom,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.ses_first_login IS NOT NULL AND b.ss_ts IS NOT NULL
              AND ABS(EXTRACT(EPOCH FROM (b.ses_first_login - b.ss_ts))::int) <= 900
         THEN 1 ELSE 0 END                                                       AS adherent_first_login,
    CASE WHEN b.ros_status IN ('SHIFT','HD') AND b.ses_last_logout IS NOT NULL AND b.se_ts IS NOT NULL
              AND EXTRACT(EPOCH FROM (b.se_ts - b.ses_last_logout))::int <= 900
         THEN 1 ELSE 0 END                                                       AS adherent_last_logout,

    15    AS fte_target,
    26    AS billing_days_target,
    28114 AS rate_per_fte

FROM base b

"""
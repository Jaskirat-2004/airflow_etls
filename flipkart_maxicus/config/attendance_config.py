# JS =============================================================================================================== JS
#                            QUERIES FOR ATTENDANCE FACT TABLE  (the WFM spine)
# JS =============================================================================================================== JS
#  LAST_DATE : 2026-09-17

# JS ======================================= DDL ======================================= JS

FLIPKART_FACT_ATTENDANCE_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS flipkart_maxicus.flipkart_fact_attendance_report
(
    report_date                Date,
    tenant_name                String,
    entity_name                String,

    hc_emp_id                  String,
    hc_employee_name           String,
    hc_designation             String,
    hc_grade                   String,
    hc_department_name         String,
    hc_employee_type           String,
    hc_location_name           String,
    hc_batch_number            String,
    hc_current_status          String,
    hc_reporting_to_name       String,
    hc_functional_rm_name      String,
    hc_date_of_joining         Nullable(Date),

    mp_ldap_id                 String,
    mp_avaya_id                String,
    mp_cohort_name             String,

    ros_status                 String,
    ros_shift                  String,
    ros_shift_type             String,
    ros_shift_start            Nullable(DateTime),
    ros_shift_end              Nullable(DateTime),

    staffed_secs               Int32,
    aux_secs                   Int32,
    actual_login_secs          Int32,
    exception_secs             Int32,
    final_login_secs           Int32,
    capped_login_secs          Int32,
    tht_secs                   Int32,

    attendance                 String,
    roster_denom               Float32,
    present_count              Float32,
    absent_count               Float32,
    planned_leave_count        Float32,
    unplanned_leave_count      Float32,
    is_present                 UInt8,
    is_absent                  UInt8,
    is_half_day                UInt8,
    is_week_off                UInt8,
    is_planned_leave           UInt8,

    login_count                Nullable(Int32),
    first_login                Nullable(DateTime),
    last_logout                Nullable(DateTime),
    delay_login_secs           Nullable(Int32),
    early_logout_secs          Nullable(Int32),
    login_adherent             Nullable(UInt8),
    logout_adherent            Nullable(UInt8),
    day_adherent               Nullable(UInt8),
    adherence_denom            Nullable(UInt8),

    week_label                 String,
    loaded_at                  DateTime DEFAULT now()
)

ENGINE = MergeTree
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, hc_emp_id)

"""


# JS ======================================= QUERY ======================================= JS

FLIPKART_FACT_ATTENDANCE_REPORT_QUERY = """

WITH mp AS (
    SELECT DISTINCT ON (maxicus_id)
           NULLIF(maxicus_id, '-')          AS emp_id,
           ldap_id                          AS ldap_id,
           NULLIF(avaya_id, '-')            AS avaya_id,
           NULLIF(sbr_primary_cohort, '-')  AS cohort_name
    FROM   mapper_dim
    WHERE  NULLIF(maxicus_id, '-') IS NOT NULL
    ORDER  BY maxicus_id, (avaya_id IS DISTINCT FROM '-') DESC
),
ros AS (
    SELECT r.report_date,
           r.emp_id,
           COALESCE(r.shift, '')                                                AS shift_label,
           CASE WHEN LOWER(TRIM(r.roster)) = 'wo'                 THEN 'WO'
                WHEN LOWER(TRIM(r.roster)) IN ('pl','leave')      THEN 'PL'
                WHEN LOWER(TRIM(r.roster)) = 'holiday'            THEN 'Holiday'
                WHEN LOWER(TRIM(r.roster)) = 'phd'                THEN 'PHD'
                WHEN LOWER(TRIM(r.roster)) IN ('hd','half day')   THEN 'HD'
                WHEN TRIM(COALESCE(r.roster,'')) = ''             THEN 'UNROSTERED'
                ELSE 'SHIFT' END                                                AS ros_status,
           substring(REPLACE(COALESCE(r.shift,''),' ',''),
                     '^([0-9]{{2}}:[0-9]{{2}})-[0-9]{{2}}:[0-9]{{2}}$')::time   AS shift_start_t,
           substring(REPLACE(COALESCE(r.shift,''),' ',''),
                     '^[0-9]{{2}}:[0-9]{{2}}-([0-9]{{2}}:[0-9]{{2}})$')::time   AS shift_end_t
    FROM   roster r
    WHERE  NULLIF(TRIM(r.emp_id),'') IS NOT NULL
),
ap AS (
    SELECT a.report_date,
           m.emp_id,
           SUM(a.staffed_secs)::int                                          AS staffed_secs,
           SUM(a.aux_secs)::int                                              AS aux_secs,
           SUM(a.acd_time_secs + a.hold_time_secs + a.acw_time_secs)::int    AS tht_secs
    FROM   apr_dump a
    JOIN   agent_identity_map m ON m.avaya_id = LOWER(TRIM(a.login_id))
                               AND a.report_date BETWEEN m.valid_from AND m.valid_to
    GROUP  BY 1, 2
),
dwn AS (
    SELECT d.report_date,
           d.emp_id,
           SUM(EXTRACT(EPOCH FROM d.downtime::interval))::int                AS exception_secs
    FROM   downtime_login_hr d
    WHERE  d.downtime ~ '^[0-9]+:[0-9]{{2}}:[0-9]{{2}}$'
    GROUP  BY 1, 2
),
lg AS (
    SELECT s.report_date,
           m.emp_id,
           COUNT(*)::int                                AS login_count,
           (s.report_date + MIN(s.login_time))          AS first_login,
           (s.report_date + MAX(s.logout_time))         AS last_logout
    FROM  (SELECT DISTINCT report_date, login_id, login_time, logout_time
             FROM login_logout_dump) s
    JOIN   agent_identity_map m ON m.avaya_id = LOWER(TRIM(s.login_id))
                               AND s.report_date BETWEEN m.valid_from AND m.valid_to
    GROUP  BY s.report_date, m.emp_id
),
calc AS (
    SELECT hc.report_date,
           hc.employee_id                                   AS emp_id,
           hc.employee_name, hc.designation_name, hc.grade, hc.department_name,
           hc.employee_type, hc.location_name, hc.batch_number, hc.current_status,
           hc.reporting_to_name, hc.functional_reporting_to_name, hc.date_of_joining,

           mp.ldap_id, mp.avaya_id, mp.cohort_name,

           COALESCE(ros.ros_status, 'UNROSTERED')           AS ros_status,
           COALESCE(ros.shift_label, '')                    AS ros_shift,
           ros.shift_start_t, ros.shift_end_t,

           COALESCE(ap.staffed_secs,    0)                  AS staffed_secs,
           COALESCE(ap.aux_secs,        0)                  AS aux_secs,
           COALESCE(ap.tht_secs,        0)                  AS tht_secs,
           COALESCE(dwn.exception_secs, 0)                  AS exception_secs,

           lg.login_count, lg.first_login, lg.last_logout,

           (COALESCE(ap.staffed_secs,0) - COALESCE(ap.aux_secs,0))
               + COALESCE(dwn.exception_secs,0)             AS final_login_secs
    FROM       head_count hc
    LEFT JOIN  mp  ON mp.emp_id       = hc.employee_id
    LEFT JOIN  ros ON ros.report_date = hc.report_date AND ros.emp_id = hc.employee_id
    LEFT JOIN  ap  ON ap.report_date  = hc.report_date AND ap.emp_id  = hc.employee_id
    LEFT JOIN  dwn ON dwn.report_date = hc.report_date AND dwn.emp_id = hc.employee_id
    LEFT JOIN  lg  ON lg.report_date  = hc.report_date AND lg.emp_id  = hc.employee_id
    WHERE      hc.report_date > DATE '{last_processed}'
),
att AS (
    SELECT c.*,
           CASE WHEN c.shift_end_t <= c.shift_start_t THEN 'Night' ELSE 'Day' END   AS ros_shift_type,
           (c.report_date + c.shift_start_t)                                        AS shift_start,
           (c.report_date + c.shift_end_t
              + CASE WHEN c.shift_end_t <= c.shift_start_t THEN INTERVAL '1 day'
                     ELSE INTERVAL '0 day' END)                                     AS shift_end,
           CASE WHEN c.ros_status IN ('WO','PL','Holiday','PHD') THEN c.ros_status
                WHEN c.final_login_secs < 14400                  THEN 'UL'
                WHEN c.final_login_secs < 27000                  THEN 'HD'
                ELSE 'Present' END                                                  AS attendance
    FROM   calc c
),
adh AS (
    SELECT a.*,
           (a.ros_status = 'SHIFT' AND a.attendance = 'Present')                    AS adh_eligible,
           EXTRACT(EPOCH FROM (a.first_login - a.shift_start))::int                 AS delay_login_secs,
           EXTRACT(EPOCH FROM (a.shift_end   - a.last_logout))::int                 AS early_logout_secs,
           ROUND(ABS(EXTRACT(EPOCH FROM (a.first_login - a.shift_start))) / 60.0)   AS delay_min,
           ROUND(    EXTRACT(EPOCH FROM (a.shift_end   - a.last_logout))  / 60.0)   AS early_min
    FROM   att a
)
SELECT
    f.report_date                                       AS report_date,
    'flipkart'                                          AS tenant_name,
    'maxicus'                                           AS entity_name,

    f.emp_id                                            AS hc_emp_id,
    COALESCE(f.employee_name, '')                       AS hc_employee_name,
    COALESCE(f.designation_name, '')                    AS hc_designation,
    COALESCE(f.grade, '')                               AS hc_grade,
    COALESCE(f.department_name, '')                     AS hc_department_name,
    COALESCE(f.employee_type, '')                       AS hc_employee_type,
    COALESCE(f.location_name, '')                       AS hc_location_name,
    COALESCE(f.batch_number, '')                        AS hc_batch_number,
    COALESCE(f.current_status, '')                      AS hc_current_status,
    COALESCE(f.reporting_to_name, '')                   AS hc_reporting_to_name,
    COALESCE(f.functional_reporting_to_name, '')        AS hc_functional_rm_name,
    f.date_of_joining::date                             AS hc_date_of_joining,

    COALESCE(f.ldap_id, '')                             AS mp_ldap_id,
    COALESCE(f.avaya_id, '')                            AS mp_avaya_id,
    COALESCE(f.cohort_name, '')                         AS mp_cohort_name,

    f.ros_status                                        AS ros_status,
    f.ros_shift                                         AS ros_shift,
    f.ros_shift_type                                    AS ros_shift_type,
    f.shift_start                                       AS ros_shift_start,
    f.shift_end                                         AS ros_shift_end,

    f.staffed_secs                                      AS staffed_secs,
    f.aux_secs                                          AS aux_secs,
    (f.staffed_secs - f.aux_secs)                       AS actual_login_secs,
    f.exception_secs                                    AS exception_secs,
    f.final_login_secs                                  AS final_login_secs,
    LEAST(f.final_login_secs, 28800)                    AS capped_login_secs,
    f.tht_secs                                          AS tht_secs,

    f.attendance                                        AS attendance,

    CASE WHEN f.attendance IN ('WO','Holiday','PL') THEN 0 ELSE 1 END::float4   AS roster_denom,
    CASE WHEN f.attendance = 'Present' THEN 1
         WHEN f.attendance = 'HD'      THEN 0.5 ELSE 0 END::float4              AS present_count,
    CASE WHEN f.attendance IN ('UL','PL') THEN 1
         WHEN f.attendance = 'HD'         THEN 0.5 ELSE 0 END::float4           AS absent_count,
    CASE WHEN f.attendance = 'PL'  THEN 1
         WHEN f.attendance = 'PHD' THEN 0.5 ELSE 0 END::float4                  AS planned_leave_count,
    CASE WHEN f.attendance = 'UL' THEN 1
         WHEN f.attendance = 'HD' THEN 0.5 ELSE 0 END::float4                   AS unplanned_leave_count,

    (f.attendance = 'Present')::int                     AS is_present,
    (f.attendance = 'UL')::int                          AS is_absent,
    (f.attendance = 'HD')::int                          AS is_half_day,
    (f.attendance = 'WO')::int                          AS is_week_off,
    (f.attendance = 'PL')::int                          AS is_planned_leave,

    f.login_count                                       AS login_count,
    f.first_login                                       AS first_login,
    f.last_logout                                       AS last_logout,
    f.delay_login_secs                                  AS delay_login_secs,
    f.early_logout_secs                                 AS early_logout_secs,

    CASE WHEN f.adh_eligible AND f.delay_min IS NOT NULL
         THEN (f.delay_min <= 10)::int END                                      AS login_adherent,
    CASE WHEN f.adh_eligible AND f.early_min IS NOT NULL
         THEN (f.early_min <= 10)::int END                                      AS logout_adherent,
    CASE WHEN f.adh_eligible AND f.delay_min IS NOT NULL AND f.early_min IS NOT NULL
         THEN (f.delay_min <= 10 AND f.early_min <= 10)::int END                AS day_adherent,
    CASE WHEN f.adh_eligible AND f.delay_min IS NOT NULL
         THEN 1 END                                                             AS adherence_denom,

    'Week-' || LEAST(CEIL(EXTRACT(DAY FROM f.report_date) / 7.0), 4)::int::text  AS week_label
FROM adh f

"""


-- PLATINUMRX has no APSI. This table is the attendance basis :
-- login_secs = last_logout - first_login. Grain = one row per (report_date, emp_id).
-- Contract : platinumrx/05-wfm-report.md section B1

CREATE TABLE platinumrx_agent_login (
    report_date   DATE        NOT NULL,
    emp_id        TEXT        NOT NULL,   -- numeric HRMS id '650881' -> TEXT, must match head_count / roster
    first_login   TIMESTAMP,              -- first login of the day
    last_logout   TIMESTAMP,              -- last logout of the day
    break_secs    INTEGER,                -- OPTIONAL, still unused by the ETL (held at 0). Fill it to remove the gross/net caveat
    PRIMARY KEY (report_date, emp_id)
);

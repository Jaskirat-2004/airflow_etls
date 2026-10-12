CREATE TABLE downtime_login_hr_staging (
    report_date       DATE,
    emp_id            TEXT,
    exception_hr      VARCHAR(8),
    reason            TEXT,
    approved_by       TEXT
);

CREATE TABLE downtime_login_hr (
    report_date       DATE,
    emp_id            TEXT,
    exception_hr      VARCHAR(8),
    reason            TEXT,
    approved_by       TEXT,
    updated_at        TIMESTAMP DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date,emp_id)
);
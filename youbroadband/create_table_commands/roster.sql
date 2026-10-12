
CREATE TABLE roster_staging (
    report_date   DATE,
    emp_id        TEXT,
    roster        TEXT
);

CREATE TABLE roster (
    report_date   DATE,
    emp_id        TEXT,
    roster        TEXT,
    updated_at    TIMESTAMP DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date, emp_id)
);
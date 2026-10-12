CREATE TABLE roster_staging (
    report_date   DATE,
    emp_id        TEXT,
    roster        TEXT
);


CREATE TABLE roster (
    report_date   DATE,
    emp_id        TEXT,
    roster        TEXT,
    updated_at    TIMESTAMP,
    PRIMARY KEY(report_date,emp_id) 
);
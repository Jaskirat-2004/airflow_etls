
CREATE TABLE roster_staging (
    report_date   DATE,
    emp_id        TEXT,
    roster        TEXT
);


CREATE TABLE roster (
    report_date   DATE        NOT NULL,
    emp_id        TEXT        NOT NULL,
    roster        TEXT,
    updated_at    TIMESTAMP   DEFAULT NOW(),   
    PRIMARY KEY (report_date, emp_id)
);
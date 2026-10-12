


CREATE TABLE roster_staging (
    report_date    DATE,
    ldap_id        TEXT,     -- 'maxam.NNNNNN'
    emp_id         TEXT,     -- the MAXICUS id -> head_count.employee_id
    shift          TEXT,     -- '09:00 - 18:00' | '12:00 - 21:00'
    roster         TEXT      -- the shift string when working, else WO / PL / HD / Holiday / PHD
);

CREATE TABLE roster (
    report_date    DATE NOT NULL,
    ldap_id        TEXT NOT NULL,
    emp_id         TEXT NOT NULL,
    shift          TEXT,
    roster         TEXT,
    updated_at     TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (report_date, emp_id, ldap_id)
);

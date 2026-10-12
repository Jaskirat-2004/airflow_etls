
CREATE TABLE platinumrx_roster (
    report_date   DATE        NOT NULL,
    emp_id        TEXT        NOT NULL,   -- numeric HRMS id '650881' -> TEXT
    roster        TEXT,                   -- raw '09:00 - 18:00' / 'WO' / 'PL' / 'Leave' / '-' -- keep raw
    updated_at    TIMESTAMP   DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date, emp_id)
);
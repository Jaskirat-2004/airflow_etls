
CREATE TABLE roster (
    report_date   DATE        NOT NULL,
    emp_id        TEXT        NOT NULL,   -- '803516' AND 'NAPS310552' -> TEXT
    roster        TEXT,                   -- raw '09:00 - 18:00' / 'PL' / 'HD' -- keep raw
    updated_at    TIMESTAMP   DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date, emp_id)
);
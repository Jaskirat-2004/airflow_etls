CREATE TABLE roster (
    report_date   DATE,
    emp_id        TEXT,          -- '803516' AND 'NAPS310552' → must be TEXT
    roster        TEXT           -- raw '09:00 - 18:00' / 'PL' / 'HD' — keep raw
);
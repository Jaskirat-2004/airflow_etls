
CREATE TABLE forecast_staging (
    report_date   DATE,
    forecast      INTEGER
);

CREATE TABLE forecast (
    report_date   DATE,
    forecast      INTEGER,
    updated_at    TIMESTAMP DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date)
);
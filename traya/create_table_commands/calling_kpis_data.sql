-- calling_kpis_data: daily agent KPI dump uploaded via portal, one row per agent per day
CREATE TABLE calling_kpis_data (
    report_date         DATE,                -- date of the dump, set by agent at upload
    employee_id         VARCHAR(50),
    coach_name          VARCHAR(255),
    tl_name             VARCHAR(255),
    process             VARCHAR(255),
    location            VARCHAR(255),
    num_attempted       SMALLINT,
    num_answered        SMALLINT,
    num_unanswered      SMALLINT,
    total_time_spent    INTEGER,
    talk_time           INTEGER,
    calls_over_20m      SMALLINT,
    miss_match_count    SMALLINT
);
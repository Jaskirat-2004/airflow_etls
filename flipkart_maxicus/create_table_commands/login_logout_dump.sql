
CREATE TABLE IF NOT EXISTS login_logout_dump_staging (
    report_date   DATE,      -- DERIVED: logout_date, minus 1 day if logout_time < login_time
    agent_name    TEXT,
    login_id      TEXT,      -- the AVAYA extension -> agent_identity_map.client_id
    extn          TEXT,      -- the desk phone; carried, never joined on
    login_time    TIME,
    logout_time   TIME,
    logout_date   DATE
);

CREATE TABLE IF NOT EXISTS login_logout_dump (
    report_date   DATE      NOT NULL,
    agent_name    TEXT,
    login_id      TEXT      NOT NULL,
    extn          TEXT,
    login_time    TIME      NOT NULL,
    logout_time   TIME,
    logout_date   DATE,
    updated_at    TIMESTAMP DEFAULT NOW()

    PRIMARY KEY (report_date, login_id, login_time)
);
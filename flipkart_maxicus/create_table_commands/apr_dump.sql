CREATE TABLE apr_dump_staging (
    report_date              DATE,
    login_name               TEXT,          -- client col 1 'Login ID' (agent NAME) - untrusted display text
    login_id                 TEXT,          -- client col 2 'Login ID' (extension) - int in the file, load as TEXT
    acd_calls                INTEGER,
    acd_time_secs            INTEGER,
    hold_time_secs           INTEGER,
    acw_time_secs            INTEGER,
    ring_time_secs           INTEGER,
    avail_time_secs          INTEGER,
    staffed_secs             INTEGER,
    trans_out                INTEGER,
    conf                     INTEGER,
    acd_calls_released       INTEGER,
    aux_secs                 INTEGER,
    -- equals the sum of the 10 buckets below
    aux_default_secs         INTEGER,
    aux_tea_break_secs       INTEGER,
    aux_floor_support_secs   INTEGER,
    aux_lunch_secs           INTEGER,
    aux_training_secs        INTEGER,
    aux_feedback_secs        INTEGER,
    aux_meeting_secs         INTEGER,
    aux_system_issue_secs    INTEGER,
    aux_callback_secs        INTEGER,
    aux_logout_secs          INTEGER,
    extn_out_calls           INTEGER
);


CREATE TABLE apr_dump (
    report_date              DATE,
    login_name               TEXT, 
    login_id                 TEXT,
    acd_calls                INTEGER,
    acd_time_secs            INTEGER,
    hold_time_secs           INTEGER,
    acw_time_secs            INTEGER,
    ring_time_secs           INTEGER,
    avail_time_secs          INTEGER,
    staffed_secs             INTEGER,
    trans_out                INTEGER,
    conf                     INTEGER,
    acd_calls_released       INTEGER,
    aux_secs                 INTEGER,
    -- equals the sum of the 10 buckets below
    aux_default_secs         INTEGER,
    aux_tea_break_secs       INTEGER,
    aux_floor_support_secs   INTEGER,
    aux_lunch_secs           INTEGER,
    aux_training_secs        INTEGER,
    aux_feedback_secs        INTEGER,
    aux_meeting_secs         INTEGER,
    aux_system_issue_secs    INTEGER,
    aux_callback_secs        INTEGER,
    aux_logout_secs          INTEGER,
    extn_out_calls           INTEGER,

    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (report_date, login_id)
);
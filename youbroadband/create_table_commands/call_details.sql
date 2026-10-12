
CREATE TABLE call_details_staging (
    report_date              DATE,
    row_num                  INTEGER,
    call_id                  TEXT,
    crt_object_id            TEXT,        -- NEW
    call_time                TIMESTAMP,
    process_name             TEXT,
    campaign_name            TEXT,
    queue_name               TEXT,        -- NEW
    lead_id                  TEXT,
    lead_name                TEXT,
    phone                    TEXT,        -- TEXT, never numeric
    did                      TEXT,        -- NEW
    other_filter_groups      TEXT,
    applied_filter_group     TEXT,
    table_filters            TEXT,
    customer_id              TEXT,        -- '-1' sentinel
    call_type                TEXT,
    system_disposition       TEXT,
    hangup_cause_code        INTEGER,
    hangup_details           TEXT,
    customer_setup_time      TEXT,
    customer_ringing_time    TEXT,
    ivr_time                 TEXT,        -- HH:MM:SS here, ms in ivr_hungup
    customer_talk_time       TEXT,
    customer_hold_duration   TEXT,
    actual_channel           TEXT,
    num_attempts             INTEGER,
    association_type         TEXT,
    user_id                  TEXT,
    user_name                TEXT,
    disposition_code         TEXT,
    disposition_class        TEXT,
    transfer_to_agent_phone  TEXT,
    user_setup_time          TEXT,
    user_ringing_time        TEXT,
    user_talk_time           TEXT,
    acw_duration             TEXT,
    call_notes               TEXT
);

CREATE TABLE call_details (
    report_date              DATE,
    row_num                  INTEGER,
    call_id                  TEXT,
    crt_object_id            TEXT,        -- NEW
    call_time                TIMESTAMP,
    process_name             TEXT,
    campaign_name            TEXT,
    queue_name               TEXT,        -- NEW
    lead_id                  TEXT,
    lead_name                TEXT,
    phone                    TEXT,        -- TEXT, never numeric
    did                      TEXT,        -- NEW
    other_filter_groups      TEXT,
    applied_filter_group     TEXT,
    table_filters            TEXT,
    customer_id              TEXT,        -- '-1' sentinel
    call_type                TEXT,
    system_disposition       TEXT,
    hangup_cause_code        INTEGER,
    hangup_details           TEXT,
    customer_setup_time      TEXT,
    customer_ringing_time    TEXT,
    ivr_time                 TEXT,        -- HH:MM:SS here, ms in ivr_hungup
    customer_talk_time       TEXT,
    customer_hold_duration   TEXT,
    actual_channel           TEXT,
    num_attempts             INTEGER,
    association_type         TEXT,
    user_id                  TEXT,
    user_name                TEXT,
    disposition_code         TEXT,
    disposition_class        TEXT,
    transfer_to_agent_phone  TEXT,
    user_setup_time          TEXT,
    user_ringing_time        TEXT,
    user_talk_time           TEXT,
    acw_duration             TEXT,
    call_notes               TEXT,
    updated_at               TIMESTAMP DEFAULT NOW(),   -- when this row was last merged (audit/debug)
    PRIMARY KEY (report_date, call_id)
);
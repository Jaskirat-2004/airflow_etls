-- acd_call_details: inbound/outbound call records with agent handling details
CREATE TABLE acd_call_details (
    row_num               INTEGER,
    campaign              VARCHAR(255),
    phone                 VARCHAR(50),
    display_phone         VARCHAR(50),
    unique_id             VARCHAR(100),
    other_filter          VARCHAR(255),
    applied_filter        VARCHAR(255),
    table_filter          VARCHAR(255),
    dnis                  VARCHAR(50),
    call_type             VARCHAR(50),
    call_id               VARCHAR(100),
    answered              VARCHAR(50),
    call_time             TIMESTAMP,
    queue_id              INTEGER,
    queue_name            VARCHAR(255),
    wait_time             VARCHAR(8),    -- HH:MM:SS
    total_wait            VARCHAR(8),    -- HH:MM:SS
    hangup_details        VARCHAR(100),
    customer_hold         VARCHAR(8),    -- HH:MM:SS
    actual_channel        VARCHAR(255),
    username              VARCHAR(255),
    user_id               VARCHAR(100),
    user_setup_time       VARCHAR(8),    -- HH:MM:SS
    user_ringing_time     VARCHAR(8),    -- HH:MM:SS
    user_talk_time        VARCHAR(8),    -- HH:MM:SS
    user_hold_time        VARCHAR(8),    -- HH:MM:SS
    cumulative_time       VARCHAR(8),    -- HH:MM:SS
    acw_duration          VARCHAR(8),    -- HH:MM:SS
    user_disposition      VARCHAR(255),
    call_notes            TEXT
);
-- call_history: complete call log with IVR, queue, agent disposition and transfer details
CREATE TABLE call_history (
    setup_id                VARCHAR(100),
    setup_name              VARCHAR(255),
    call_id                 VARCHAR(100),
    crt_object_id           VARCHAR(100),
    call_time               TIMESTAMP,
    process_name            VARCHAR(255),
    campaign_name           VARCHAR(255),
    queue_name              VARCHAR(255),
    lead_id                 VARCHAR(100),
    lead_name               VARCHAR(255),
    phone                   VARCHAR(50),
    display_phone           VARCHAR(50),
    unique_identifier       VARCHAR(100),
    did                     VARCHAR(50),
    other_filter_groups     VARCHAR(255),
    applied_filter_group    VARCHAR(255),
    table_filters           VARCHAR(255),
    customer_id             VARCHAR(50),
    call_type               VARCHAR(50),
    system_disposition      VARCHAR(100),
    hangup_cause_code       VARCHAR(50),
    hangup_details          VARCHAR(100),
    customer_setup_time     VARCHAR(8),    -- HH:MM:SS
    customer_ringing_time   VARCHAR(8),    -- HH:MM:SS
    ivr_time                VARCHAR(8),    -- HH:MM:SS
    customer_talk_time      VARCHAR(8),    -- HH:MM:SS
    customer_hold_duration  VARCHAR(8),    -- HH:MM:SS
    actual_channel          VARCHAR(255),
    attempt_number          SMALLINT,
    association_type        VARCHAR(100),
    user_id                 VARCHAR(100),
    user_name               VARCHAR(255),
    disposition_code        VARCHAR(100),
    disposition_class       VARCHAR(100),
    transfer_to_agent_phone VARCHAR(255),
    user_setup_time         VARCHAR(8),    -- HH:MM:SS
    user_ringing_time       VARCHAR(8),    -- HH:MM:SS
    user_talk_time          VARCHAR(8),    -- HH:MM:SS
    acw_duration            VARCHAR(8),    -- HH:MM:SS
    call_notes              TEXT
);
-- agent_session_details: agent login/logout and ready/break state per session
CREATE TABLE agent_session_details (
    report_date                 DATE,  
    user_id                     VARCHAR(100),
    username                    VARCHAR(255),
    session_id                  VARCHAR(500),  -- long hash-based ID
    login_time                  TIMESTAMP,
    logout_time                 TIMESTAMP,
    total_login_duration        VARCHAR(8),    -- HH:MM:SS
    campaign_id                 SMALLINT,
    campaign_name               VARCHAR(255),
    ready_history_id            VARCHAR(100),
    ready_start_time            TIMESTAMP,
    ready_end_time              TIMESTAMP,
    break_end_time              TIMESTAMP,
    break_reason                VARCHAR(255),
    ready_duration              VARCHAR(8),    -- HH:MM:SS
    break_duration              VARCHAR(8),    -- HH:MM:SS
    auto_call_on_off_history_id VARCHAR(100),
    auto_call_on_start_time     TIMESTAMP,
    auto_call_on_end_time       TIMESTAMP,
    auto_call_off_end_time      TIMESTAMP,
    auto_call_on_duration       VARCHAR(8),    -- HH:MM:SS
    auto_call_off_duration      VARCHAR(8)     -- HH:MM:SS
);


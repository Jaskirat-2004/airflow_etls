-- agent_productivity_interval_summary: per-agent metrics in 30-min intervals
CREATE TABLE agent_productivity_interval_summary (
    interval_start                              TIMESTAMP,
    interval_end                                TIMESTAMP,
    process_name                                VARCHAR(255),
    campaign_name                               VARCHAR(255),
    user_name                                   VARCHAR(255),
    user_id                                     VARCHAR(100),
    total_staffed_duration                      VARCHAR(8),    -- HH:MM:SS
    total_ready_duration                        VARCHAR(8),    -- HH:MM:SS
    total_break_duration                        VARCHAR(8),    -- HH:MM:SS
    total_idle_time                             VARCHAR(8),    -- HH:MM:SS
    total_service_time                          VARCHAR(8),    -- HH:MM:SS
    avg_ringing_time                            VARCHAR(8),    -- HH:MM:SS
    avg_talk_time                               VARCHAR(8),    -- HH:MM:SS
    avg_acw_duration                            VARCHAR(8),    -- HH:MM:SS
    total_wrapped_calls                         SMALLINT,
    avg_handling_time                           VARCHAR(8),    -- HH:MM:SS
    total_talk_time_in_interval                 VARCHAR(8),    -- HH:MM:SS
    total_acw_duration_in_interval              VARCHAR(8),    -- HH:MM:SS
    auto_call_on_duration                       VARCHAR(8),    -- HH:MM:SS
    auto_call_off_duration                      VARCHAR(8),    -- HH:MM:SS
    auto_dials                                  SMALLINT,
    auto_preview_dials                          SMALLINT,
    inbound_received                            SMALLINT,
    manual_dials                                SMALLINT,
    manual_preview_dials                        SMALLINT,
    callbacks_received                          SMALLINT,
    transfers_received                          SMALLINT,
    auto_dialer_ring_time                       VARCHAR(8),    -- HH:MM:SS
    auto_preview_ring_time                      VARCHAR(8),    -- HH:MM:SS
    inbound_ring_time                           VARCHAR(8),    -- HH:MM:SS
    manual_ring_time                            VARCHAR(8),    -- HH:MM:SS
    manual_preview_ring_time                    VARCHAR(8),    -- HH:MM:SS
    callback_calls_ring_time                    VARCHAR(8),    -- HH:MM:SS
    transfer_to_campaign_ring_time              VARCHAR(8),    -- HH:MM:SS
    click_to_calls_ring_time                    VARCHAR(8),    -- HH:MM:SS
    auto_dialer_calls_talk_time                 VARCHAR(8),    -- HH:MM:SS
    auto_preview_talk_time                      VARCHAR(8),    -- HH:MM:SS
    inbound_calls_talk_time                     VARCHAR(8),    -- HH:MM:SS
    manual_calls_talk_time                      VARCHAR(8),    -- HH:MM:SS
    manual_preview_talk_time                    VARCHAR(8),    -- HH:MM:SS
    callback_calls_talk_time                    VARCHAR(8),    -- HH:MM:SS
    transfer_to_campaign_calls_talk_time        VARCHAR(8),    -- HH:MM:SS
    click_to_call_talk_time                     VARCHAR(8),    -- HH:MM:SS
    auto_dialer_calls_acw_duration              VARCHAR(8),    -- HH:MM:SS
    auto_preview_calls_acw_duration             VARCHAR(8),    -- HH:MM:SS
    inbound_calls_acw_duration                  VARCHAR(8),    -- HH:MM:SS
    manual_calls_acw_duration                   VARCHAR(8),    -- HH:MM:SS
    preview_manual_calls_acw_duration           VARCHAR(8),    -- HH:MM:SS
    callback_calls_acw_duration                 VARCHAR(8),    -- HH:MM:SS
    transfer_to_campaign_calls_acw_duration     VARCHAR(8),    -- HH:MM:SS
    click_to_calls_acw_duration                 VARCHAR(8),    -- HH:MM:SS  <-- ACW done, counts start now
    connected_auto_dials                        SMALLINT,
    connected_inbound                           SMALLINT,
    connected_manual_dials                      SMALLINT,
    connected_callbacks                         SMALLINT,
    connected_transfers                         SMALLINT,
    total_customer_hold_duration                VARCHAR(8),    -- HH:MM:SS
    avg_customer_hold_duration                  VARCHAR(8),    -- HH:MM:SS
    connected_manual_preview_dials              SMALLINT,
    connected_auto_preview_dials                SMALLINT,
    click_to_calls                              SMALLINT,
    connected_click_to_calls                    SMALLINT,
    total_ring_time                             VARCHAR(8),    -- HH:MM:SS
    total_preview_time                          VARCHAR(8),    -- HH:MM:SS
    avg_preview_time                            VARCHAR(8)     -- HH:MM:SS
);
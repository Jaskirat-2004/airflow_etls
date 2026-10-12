CREATE TABLE ivr_footprint_staging (
    report_date                 DATE,
    row_num                     INTEGER,
    campaign_name               TEXT,
    phone_number                TEXT,       -- TEXT, never numeric
    call_datetime               TIMESTAMP,
    call_id                     TEXT,
    system_disposition          TEXT,
    queue_initiate_time         TEXT,
    ivr_time                    INTEGER,    -- milliseconds (36148 ≈ 36s)
    language_selection_input    TEXT,
    api_1_response              TEXT,       -- 'TRUE', not numeric
    api_2_response              TEXT,       -- JSON
    query_menu_input            TEXT,
    api_3_response_fresh_open   TEXT,       -- JSON
    fresh_complaint_menu        TEXT,
    open_complaint_menu         TEXT,
    customer_type_menu          TEXT,
    enter_number_input          TEXT,
    account_menu                TEXT,
    recharge_menu               TEXT,
    api_4_response              TEXT,       -- JSON
    api_5_response              TEXT,
    api_6_response              TEXT,
    hangup_node_detail          TEXT,
    queue_name                  TEXT
);

CREATE TABLE ivr_footprint (
    report_date                 DATE,
    row_num                     INTEGER,
    campaign_name               TEXT,
    phone_number                TEXT,       -- TEXT, never numeric
    call_datetime               TIMESTAMP,
    call_id                     TEXT,
    system_disposition          TEXT,
    queue_initiate_time         TEXT,
    ivr_time                    INTEGER,    -- milliseconds (36148 ≈ 36s)
    language_selection_input    TEXT,
    api_1_response              TEXT,       -- 'TRUE', not numeric
    api_2_response              TEXT,       -- JSON
    query_menu_input            TEXT,
    api_3_response_fresh_open   TEXT,       -- JSON
    fresh_complaint_menu        TEXT,
    open_complaint_menu         TEXT,
    customer_type_menu          TEXT,
    enter_number_input          TEXT,
    account_menu                TEXT,
    recharge_menu               TEXT,
    api_4_response              TEXT,       -- JSON
    api_5_response              TEXT,
    api_6_response              TEXT,
    hangup_node_detail          TEXT,
    queue_name                  TEXT,
    updated_at                  TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (report_date, call_id)
);

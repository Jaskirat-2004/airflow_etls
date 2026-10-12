CREATE TABLE tagging_dump_staging (
    report_date              DATE,
    session_id               TEXT,
    incident_creation_time   TIMESTAMP,
    incident_id              TEXT,
    thread_id                TEXT,          -- int in the file, load as TEXT - this is the key
    thread_created_at        TIMESTAMP,     -- report_date derives from THIS
    thread_created_by        TEXT,
    queue_name               TEXT,
    thread_type              TEXT,
    thread_entry_type_name   TEXT,
    status_name              TEXT,
    lockin_flag              TEXT,
    order_id                 TEXT,
    issue_name               TEXT,
    sub_issue_name           TEXT,
    sub_sub_issue_name       TEXT,
    channel_id               TEXT,
    tenant_name              TEXT,
    thread_text              TEXT,
    partner_location         TEXT 
);

CREATE TABLE tagging_dump (
    report_date              DATE,
    session_id               TEXT,
    incident_creation_time   TIMESTAMP,
    incident_id              TEXT,
    thread_id                TEXT,          -- int in the file, load as TEXT - this is the key
    thread_created_at        TIMESTAMP,     -- report_date derives from THIS
    thread_created_by        TEXT,
    queue_name               TEXT,
    thread_type              TEXT,
    thread_entry_type_name   TEXT,
    status_name              TEXT,
    lockin_flag              TEXT,
    order_id                 TEXT,
    issue_name               TEXT,
    sub_issue_name           TEXT,
    sub_sub_issue_name       TEXT,
    channel_id               TEXT,
    tenant_name              TEXT,
    thread_text              TEXT,
    partner_location         TEXT,

    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (report_date,thread_id)
);
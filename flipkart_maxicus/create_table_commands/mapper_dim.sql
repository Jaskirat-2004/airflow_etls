
CREATE TABLE mapper_dim (
    ldap_id                   TEXT,   -- the join spine. 'maxam.NNNNNN'
    maxicus_id                TEXT,   -- MIXED float/str: 808851 and NAPS310798. NEVER numeric
    employee_full_name        TEXT,   -- NOT unique
    batch_no                  TEXT,
    production_date           TEXT,   -- '-' on 270 of 416. AON is derived from this
    hc_status                 TEXT,   -- client 'Status' - Active/Inactive
    certification_status      TEXT,
    trainer_name              TEXT,
    trainer_ldap_id           TEXT,   -- MIXED: an email on some rows, an LDAP on others
    training_lob              TEXT,
    sub_training_lob          TEXT,
    training_base_lob_skill   TEXT,
    nht_start_date            TEXT,
    ojt_start_date            TEXT,
    cert_start_date           TEXT,
    support_centre_name       TEXT,
    channel                   TEXT,
    designation               TEXT,
    attrition_date            TEXT,   -- '-' on 311 of 416
    doj                       TEXT,
    avaya_id                  TEXT,   -- '-' on 66 of 416 - those agents are invisible in every Avaya metric
    team                      TEXT,
    wfh_wfo                   TEXT,
    agent_location            TEXT,   -- client 'Location of Agents'
    gsuite_id                 TEXT,   -- NOT unique
    movement_date             TEXT,   -- '-' on 415 of 416
    team_leader_name          TEXT,
    manager_name              TEXT,
    queue_0_30                TEXT,   -- '-' on all 416
    floor_queue_name          TEXT,   -- '-' on all 416
    partner_center_name       TEXT,
    team_leader_ldap_id       TEXT,
    current_lob               TEXT,
    sub_current_lob           TEXT,   -- client header has a LEADING space
    current_lob_skill         TEXT,
    cross_utilized_lob        TEXT,
    sub_cross_utilized_lob    TEXT,   -- client header has a LEADING space
    cross_utilized_lob_skill  TEXT,   -- client header 'Cross UtilizedLOBs SKILL' - MISSING space
    blended_non_blended       TEXT,
    payroll                   TEXT,   -- '-' on all 416
    certification_date        TEXT,   -- client 'Certification Date'
    agent_email_id            TEXT,
    team_lead_email_id        TEXT,
    manager_email_id          TEXT,
    sbr_primary_cohort        TEXT,   -- Catchall RE IB / Return RE IB - THE cohort source
    data_source               TEXT,
    reason_of_attrition       TEXT,
    remarks                   TEXT,
    status_internal           TEXT   -- client 'Status Internal'. Production / OJT / Training.
                                     -- This is what the RR sheet publishes as 'Department Name'
                                     -- (collapsed there to Production / OJT). CURRENT STATE only.
);
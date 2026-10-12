
CREATE TABLE rr_dump (
    report_date                     DATE     ,   -- the business date you set at upload. On Sep, floor(Response_Date) = it, 1375/1375
    incident_id                     TEXT     ,   -- candidate key part 1
    response                        TEXT     ,   -- 'Yes' / 'No' - the whole metric
    question_id                     TEXT     ,
    response_date                   DATE     ,   -- drives the report; typed
    response_datetime               TIMESTAMP,   -- candidate key part 2 - TYPED so a format change cannot create a duplicate
    incident_created_by             TEXT     ,
    issue_type                      TEXT     ,
    sub_issue_type                  TEXT     ,
    sub_sub_issue_type              TEXT     ,   -- drives the SSI-wise block
    current_queue_name              TEXT     ,
    incident_first_solved_time      TIMESTAMP,   -- the APR-path attribution date; typed because a join key depends on it
    incident_last_solved_time       TEXT     ,
    incident_first_solved_agent_id  TEXT     ,
    first_queue_name                TEXT     ,
    resolution_deadline_breached    TEXT     ,
    approved_date_time              TEXT     ,
    order_created_at                TEXT     ,
    incident_creation_date          TEXT     ,
    incident_last_solved_agent_id   TEXT     ,
    assigned_to_agent_at            TEXT     ,
    courier_partner                 TEXT     ,
    account_id                      TEXT     ,
    lockin_flag                     TEXT     ,
    order_external_id               TEXT     ,
    order_item_id_list              TEXT     ,   -- 18-digit, never a bigint
    marketplace_id                  TEXT     ,
    product_id                      TEXT     ,
    analytic_business_unit          TEXT     ,
    analytic_category               TEXT     ,
    analytic_sub_category           TEXT     ,
    analytic_super_category         TEXT     ,
    analytic_vertical               TEXT     ,
    incident_ijs_score              TEXT     ,   -- meaning unknown - do not chart
    pincode                         TEXT     ,   -- leading zeros matter
    city                            TEXT     ,
    state                           TEXT     ,
    city_tier                       TEXT     ,
    is_shopsy_order                 TEXT     ,
    grocery_nl                      TEXT     ,   -- MIXED bool/str at every refresh boundary
    partner_center                  TEXT     ,   -- client 'PartnerCenter'
    incident_channel                TEXT     ,
    response_flag                   TEXT     ,   -- 1/0 - identical to response='Yes'
    res_month                       TEXT     ,
    res_year                        TEXT     ,
    res_week                        TEXT     ,
    lob                             TEXT     ,
    support_type                    TEXT     ,
    support_partner_center          TEXT     ,
    agent_response_channel          TEXT     ,
    delivery_group                  TEXT     ,
    production_date                 TEXT     ,   -- client 'Production_Date'. AON is derived from the MAPPER, not this
    journey_node                    TEXT     ,
    rr_applicable_flag              TEXT     ,
    agent_id                        TEXT     ,   -- LDAP 'maxam.NNNNN' - THE join key. 0 unmatched against the mapper
    team                            TEXT     ,
    sub_lob                         TEXT     ,
    tenure_days                     TEXT     ,   -- = response_date - certification_date, 1375/1375. Can be negative
    tenure_bucket                   TEXT     ,   -- A_OJT when tenure_days < 0. NOT the AON bucket
    agent_status                    TEXT     ,
    certification_status            TEXT     ,
    dtl_response_channel            TEXT     ,
    doj                             TEXT     ,
    certification_date              TEXT     ,   -- client 'Cerfication_Date' [sic]
    proactive_flag                  TEXT     ,
    frm_flag                        TEXT     ,
    sbr_primary_cohort              TEXT     ,   -- Catchall RE IB / Return RE IB
    agent_touch_flag                TEXT     ,   -- MIXED int/str
    vip_lockin_context              TEXT     ,
    wfh_wfo                         TEXT     ,
    ocr_classification              TEXT     ,
    prexo_flag                      TEXT     ,
    user_lockin_state               TEXT     
);

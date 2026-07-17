# JS =============================================================================================================== JS
#                       QUERIES FOR LEADS (LEAD) FACT TABLE - VODAFONE
# JS =============================================================================================================== JS

# JS ======================================= DDL  ======================================= JS

VODAFONE_FACT_LEADS_REPORT_DDL = """

CREATE TABLE IF NOT EXISTS vodafone.vodafone_fact_leads_report
(
    report_date            Date,
    week                   String,
    tenant_name            String,
    entity_name            String,
    lead_number            String,
    prospect_id            Nullable(String),
    neogold_lead_id        Nullable(String),
    ameyo_lead_id          Nullable(String),
    mobile_number          Nullable(String),
    alternate_phone_number Nullable(String),
    dn_number              Nullable(String),
    name                   Nullable(String),
    lead_name              Nullable(String),
    lead_source            Nullable(String),
    source_campaign        Nullable(String),
    campaign_term          Nullable(String),
    campaign_name          Nullable(String),
    priority               Nullable(String),
    dialer                 Nullable(String),
    circle_code            Nullable(String),
    circle                 Nullable(String),
    city_raw               Nullable(String),
    state                  Nullable(String),
    pincode                Nullable(String),
    country                Nullable(String),
    address_1              Nullable(String),
    address_2              Nullable(String),
    lead_stage             Nullable(String),
    order_status           Nullable(String),
    lead_quality           Nullable(String),
    plan_chosen            Nullable(String),
    journey_type           Nullable(String),
    segment                Nullable(String),
    pre_or_post            Nullable(String),
    family_plan            Nullable(String),
    activation_type        Nullable(String),
    customer_type          Nullable(String),
    fulfilment_option      Nullable(String),
    order_id               Nullable(String),
    parent_order_id        Nullable(String),
    order_value            Nullable(String),
    is_serviceable         Nullable(String),
    is_lp                  Nullable(String),
    is_serviceable_lead    UInt8,
    is_qualified_lead      Nullable(String),
    is_blacklisted         Nullable(String),
    last_dispostion        Nullable(String),
    created_on             Nullable(DateTime),
    last_activity_date     Nullable(DateTime)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, lead_number)

"""


# JS ======================================= FACT TABLE  ======================================= JS

VODAFONE_FACT_LEADS_REPORT_QUERY = """

SELECT
    l.report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM l.report_date)/7.0)::int                    AS week,
    'vodafone'                                                                   AS tenant_name,
    'maxicus'                                                                    AS entity_name,
    l.lead_number,
    NULLIF(l.prospect_id,'')                                                     AS prospect_id,
    NULLIF(l.neogold_lead_id,'')                                                 AS neogold_lead_id,
    NULLIF(l.ameyo_lead_id,'')                                                   AS ameyo_lead_id,
    NULLIF(l.mobile_number,'')                                                   AS mobile_number,
    NULLIF(l.alternate_phone_number,'')                                          AS alternate_phone_number,
    NULLIF(l.dn_number,'')                                                       AS dn_number,
    NULLIF(l.name,'')                                                            AS name,
    NULLIF(l.lead_name,'')                                                       AS lead_name,

    COALESCE(initcap(NULLIF(trim(replace(l.lead_source,'%20','')),'')),'Blank')  AS lead_source,

    NULLIF(l.source_campaign,'')                                                 AS source_campaign,
    NULLIF(l.campaign_term,'')                                                   AS campaign_term,
    NULLIF(l.campaign_name,'')                                                   AS campaign_name,

    COALESCE(initcap(NULLIF(trim(l.telephony_campaign),'')),'Blank')             AS priority,

    COALESCE(NULLIF(trim(l.send_to_dialer),''),'Blank')                          AS dialer,

    NULLIF(l.circle_id,'')                                                       AS circle_code,

    COALESCE(NULLIF(trim(m.new_circle_code),''),'Blank')                         AS circle,

    NULLIF(l.city,'')                                                            AS city_raw,
    NULLIF(l.state,'')                                                           AS state,
    NULLIF(l.pincode,'')                                                         AS pincode,
    NULLIF(l.country,'')                                                         AS country,
    NULLIF(l.address_1,'')                                                       AS address_1,
    NULLIF(l.address_2,'')                                                       AS address_2,
    COALESCE(initcap(NULLIF(trim(l.lead_stage),'')),'Blank')                     AS lead_stage,
    COALESCE(NULLIF(trim(l.order_status),''),'Blank')                            AS order_status,
    NULLIF(l.lead_quality,'')                                                    AS lead_quality,
    NULLIF(l.plan_chosen,'')                                                     AS plan_chosen,
    COALESCE(NULLIF(trim(l.journey_type),''),'Blank')                            AS journey_type,
    NULLIF(l.segment,'')                                                         AS segment,
    NULLIF(l.pre_or_post,'')                                                     AS pre_or_post,
    NULLIF(l.family_plan,'')                                                     AS family_plan,
    NULLIF(l.activation_type,'')                                                 AS activation_type,
    NULLIF(l.customer_type,'')                                                   AS customer_type,
    NULLIF(l.fulfilment_option,'')                                               AS fulfilment_option,
    NULLIF(l.order_id,'')                                                        AS order_id,
    NULLIF(l.parent_order_id,'')                                                 AS parent_order_id,
    NULLIF(l.order_value,'')                                                     AS order_value,
    NULLIF(l.is_serviceable,'')                                                  AS is_serviceable,
    NULLIF(l.is_lp,'')                                                           AS is_lp,

    (CASE WHEN lower(l.is_serviceable)='yes' OR lower(l.is_lp)='yes' THEN 1 ELSE 0 END) AS is_serviceable_lead,

    NULLIF(l.is_qualified_lead,'')                                               AS is_qualified_lead,
    NULLIF(l.is_blacklisted,'')                                                  AS is_blacklisted,
    NULLIF(l.last_dispostion,'')                                                 AS last_dispostion,
    l.created_on,
    l.last_activity_date

FROM lead_master l

LEFT JOIN city_mapper m 
    ON upper(trim(l.circle_id)) = upper(trim(m.old_circle_code))

WHERE l.report_date > '{last_processed}' 
    AND l.report_date <= '{high_water_mark}'

"""


SELECT
    report_date,
    'Week-' || CEIL(EXTRACT(DAY FROM report_date)/7.0)::int          AS week,
    'vodafone'                                                       AS tenant_name,
    'maxicus'                                                        AS entity_name,
    activity_id,

    NULLIF(activity_event_name,'')                                  AS activity_event_name,
    NULLIF(lead_number,'')                                          AS lead_number,
    NULLIF(prospect_id,'')                                          AS prospect_id,
    NULLIF(phone_number,'')                                         AS phone,
    NULLIF(lead_name,'')                                            AS lead_name,
    NULLIF(pincode,'')                                              AS pincode,
    NULLIF(owner_user_name,'')                                      AS agent,
    NULLIF(owner_user_email,'')                                     AS agent_email,
    NULLIF(owner_user_id,'')                                        AS agent_user_id,

    -- Disposition categoricals: label blanks + Title-case (initcap) so case/format variants group as one
    COALESCE(initcap(NULLIF(trim(outcome),'')), 'Blank')               AS outcome,
    COALESCE(initcap(NULLIF(trim(interested_outcome),'')), 'Blank')    AS interested_outcome,
    COALESCE(initcap(NULLIF(trim(not_interested_reason),'')), 'Blank') AS not_interested_reason,
    COALESCE(initcap(NULLIF(trim(order_outcome),'')), 'Blank')         AS order_outcome,
    COALESCE(initcap(NULLIF(trim(order_action_outcome),'')), 'Blank')  AS order_action_outcome,
    COALESCE(initcap(NULLIF(trim(order_cancelled_reason),'')), 'Blank') AS order_cancelled_reason,

    NULLIF(notes,'')                                                AS notes,
    follow_up_date_and_time                                         AS follow_up_date,
    activity_date                                                   AS activity_date

FROM pc_collated_dump
WHERE report_date > '{last_processed}' 
    AND report_date <= '{high_water_mark}'




-- agent_productivity_interval_summary 
WITH ap AS (
    SELECT
        report_date AS report_date,
        lower(trim(user_id)) AS agent_email,
        campaign_name AS campaign_name,
        
        COUNT(*) AS ap_intervals,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_staffed_duration),'')::interval),0))::bigint          AS ap_staffed_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_ready_duration),'')::interval),0))::bigint            AS ap_ready_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_break_duration),'')::interval),0))::bigint            AS ap_break_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_idle_time),'')::interval),0))::bigint                 AS ap_idle_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_service_time),'')::interval),0))::bigint              AS ap_service_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_talk_time_in_interval),'')::interval),0))::bigint     AS ap_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_acw_duration_in_interval),'')::interval),0))::bigint  AS ap_acw_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_customer_hold_duration),'')::interval),0))::bigint    AS ap_hold_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(total_ring_time),'')::interval),0))::bigint                 AS ap_ring_secs,
        
        -- OFFERED components (6)
        SUM(auto_dials)                       AS ap_auto_dials,
        SUM(auto_preview_dials)               AS ap_auto_preview_dials,
        SUM(inbound_received)                 AS ap_inbound_received,
        SUM(manual_dials)                     AS ap_manual_dials,
        SUM(manual_preview_dials)             AS ap_manual_preview_dials,
        SUM(callbacks_received)               AS ap_callbacks_received,
        
        SUM(transfers_received)               AS ap_transfers_received,   -- (not in offered/answered, kept)
        SUM(total_wrapped_calls)              AS ap_wrapped_calls,
        
        -- ANSWERED components (7)
        SUM(connected_auto_dials)             AS ap_connected_auto,
        SUM(connected_inbound)                AS ap_connected_inbound,
        SUM(connected_manual_dials)           AS ap_connected_manual,
        SUM(connected_callbacks)              AS ap_connected_callbacks,
        SUM(connected_manual_preview_dials)   AS ap_connected_manual_preview,
        SUM(connected_auto_preview_dials)     AS ap_connected_auto_preview,
        SUM(click_to_calls)                   AS ap_click_to_calls,
        SUM(connected_click_to_calls)         AS ap_connected_click_to_calls,
        SUM(connected_transfers)              AS ap_connected_transfers

    FROM agent_productivity_interval_summary
    WHERE lower(user_id) LIKE '%maxicus%'
    GROUP BY 1,2,3),

-- call_history 
ch AS (
    SELECT 
        call_time::date AS report_date, -- selecting date from call_time
        lower(trim(user_id)) AS agent_email,
        campaign_name AS campaign_name,

        -- NEW METRICS
        COUNT(*)                                                                    AS ch_calls,
        COUNT(*) FILTER (WHERE call_type LIKE 'inbound%')                           AS ch_inbound_calls,
        COUNT(*) FILTER (WHERE call_type LIKE 'outbound%')                          AS ch_outbound_calls,
        COUNT(*) FILTER (WHERE system_disposition='CONNECTED')                      AS ch_connected,
        COUNT(*) FILTER (WHERE system_disposition<>'CONNECTED')                     AS ch_not_connected,

        COUNT(*) FILTER (
            WHERE disposition_code NOT IN ('wrap.timeout','user.forced.logged.off')
            AND disposition_code IS NOT NULL)                                       AS ch_tagged,        -- Tagging

        COUNT(*) FILTER (WHERE disposition_class='Sale' OR disposition_code='Sale') AS ch_sales,
        COUNT(*) FILTER (WHERE disposition_class='Voicemail')                       AS ch_voicemail,
        
        -- Call Answered Hold
        COUNT(*) FILTER (
            WHERE NULLIF(trim(customer_hold_duration),'')::interval > interval '0') AS ch_answered_hold_calls,
        
        -- Short Calls
        COUNT(*) FILTER (
            WHERE system_disposition='CONNECTED'
            AND NULLIF(trim(user_talk_time),'')::interval < interval '60 sec')      AS ch_short_calls,

        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(user_talk_time),'')::interval),0))::bigint          AS ch_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(customer_talk_time),'')::interval),0))::bigint      AS ch_cust_talk_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(acw_duration),'')::interval),0))::bigint            AS ch_acw_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(customer_hold_duration),'')::interval),0))::bigint  AS ch_hold_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(ivr_time),'')::interval),0))::bigint                AS ch_ivr_secs

    FROM call_history
    WHERE lower(user_id) LIKE '%maxicus%'
    GROUP BY 1,2,3),

-- agent_session_details
ses AS (
    SELECT
        report_date AS report_date,
        lower(trim(user_id)) AS agent_email,
        campaign_name AS campaign_name,

        COUNT(DISTINCT session_id)                                                             AS ses_sessions,
        MIN(login_time)                                                                        AS ses_min_login,
        MAX(logout_time)                                                                       AS ses_max_logout,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(ready_duration),'')::interval),0))::bigint AS ses_ready_secs,
        SUM(COALESCE(EXTRACT(EPOCH FROM NULLIF(trim(break_duration),'')::interval),0))::bigint AS ses_break_secs
        
    FROM agent_session_details
    WHERE lower(user_id) LIKE '%maxicus%'
    GROUP BY 1,2,3),

-- master_tracker
mt AS ( 
    SELECT DISTINCT ON (report_date, lower(trim(official_email)))
        report_date AS report_date, 
        lower(trim(official_email)) AS agent_email,

        emp_id              AS mt_emp_id,
        emp_name            AS mt_emp_name, 
        designation         AS mt_designation,
        team_leader         AS mt_team_leader, 
        operations_manager  AS mt_operations_manager,
        group_name          AS mt_group_name, 
        sub_group           AS mt_sub_group, 
        line_of_business    AS mt_line_of_business,
        tenure              AS mt_tenure, 
        date_of_joining     AS mt_doj, 
        batch_number        AS mt_batch,
        versant_score       AS mt_versant, 
        active_status       AS mt_active_status, 
        gender              AS mt_gender,
        education_level     AS mt_education, 
        fresher_experience  AS mt_fresher_exp,
        
        -- Live status
        CASE
            WHEN group_name='Training' THEN 'Training'
            WHEN group_name='OJT'      THEN 'OJT'
            ELSE 'Live'
        END                 AS mt_status

    FROM master_tracker
    WHERE official_email IS NOT NULL AND official_email <> '' AND active_status = 'Active'
    ORDER BY report_date, lower(trim(official_email)), emp_id),

-- keys for the backbone of the fact table 
keys AS (
    SELECT report_date, agent_email, campaign_name FROM ap
    UNION
    SELECT report_date, agent_email, campaign_name FROM ch
    UNION
    SELECT report_date, agent_email, campaign_name FROM ses )

SELECT
    k.report_date, 
    k.agent_email, 
    k.campaign_name,
    'traya' as tenant_name,
    'maxicus' as entity_name,

    'Week-' || (
        FLOOR(
            (EXTRACT(DAY FROM k.report_date) + 
            EXTRACT(ISODOW FROM date_trunc('month', k.report_date)) - 2) / 7
            ) + 1 )::int::text  AS week,

    -- dimension (per-day)
    mt.mt_emp_id, 
    mt.mt_emp_name, 
    mt.mt_designation, 
    mt.mt_status, 
    mt.mt_team_leader, 
    mt.mt_operations_manager,
    mt.mt_group_name, 
    mt.mt_sub_group, 
    mt.mt_line_of_business, 
    mt.mt_tenure, 
    mt.mt_doj, 
    mt.mt_batch,
    mt.mt_versant, 
    mt.mt_active_status, 
    mt.mt_gender, 
    mt.mt_education, 
    mt.mt_fresher_exp,

    -- APR raw (productivity)
    ap.ap_intervals, 
    ap.ap_staffed_secs, 
    ap.ap_ready_secs, 
    ap.ap_break_secs, 
    ap.ap_idle_secs, 
    ap.ap_service_secs,
    ap.ap_talk_secs, 
    ap.ap_acw_secs, 
    ap.ap_hold_secs, 
    ap.ap_ring_secs, 
    ap.ap_wrapped_calls,
    ap.ap_auto_dials, 
    ap.ap_auto_preview_dials, 
    ap.ap_inbound_received, 
    ap.ap_manual_dials, 
    ap.ap_manual_preview_dials,
    ap.ap_callbacks_received, 
    ap.ap_transfers_received,
    ap.ap_connected_auto, 
    ap.ap_connected_inbound, 
    ap.ap_connected_manual, 
    ap.ap_connected_callbacks,
    ap.ap_connected_manual_preview, 
    ap.ap_connected_auto_preview, 
    ap.ap_click_to_calls, 
    ap.ap_connected_click_to_calls,
    ap.ap_connected_transfers,

    -- Calls Offered
    (ap.ap_auto_dials + ap.ap_auto_preview_dials + ap.ap_inbound_received + 
    ap.ap_manual_dials + ap.ap_manual_preview_dials + ap.ap_callbacks_received)              AS ap_total_offered,
    
    -- Calls Answered
    (ap.ap_connected_auto + ap.ap_connected_inbound + ap.ap_connected_manual + 
    ap.ap_connected_manual_preview + ap.ap_connected_auto_preview + ap.ap_click_to_calls)    AS ap_total_answered,

    -- call_history pivots
    COALESCE(ch.ch_calls,0) ch_calls, 
    COALESCE(ch.ch_inbound_calls,0) ch_inbound_calls, 
    COALESCE(ch.ch_outbound_calls,0) ch_outbound_calls,
    COALESCE(ch.ch_connected,0) ch_connected, 
    COALESCE(ch.ch_not_connected,0) ch_not_connected,
    COALESCE(ch.ch_tagged,0) ch_tagged, 
    COALESCE(ch.ch_sales,0) ch_sales, 
    COALESCE(ch.ch_voicemail,0) ch_voicemail,
    COALESCE(ch.ch_answered_hold_calls,0) ch_answered_hold_calls,
    COALESCE(ch.ch_short_calls,0) ch_short_calls, 
    COALESCE(ch.ch_talk_secs,0) ch_talk_secs, 
    COALESCE(ch.ch_cust_talk_secs,0) ch_cust_talk_secs,
    COALESCE(ch.ch_acw_secs,0) ch_acw_secs, 
    COALESCE(ch.ch_hold_secs,0) ch_hold_secs,
    COALESCE(ch.ch_ivr_secs,0) ch_ivr_secs,

    -- THT
    CASE 
        WHEN k.campaign_name = 'MaxicusAmritsar_Outbound_Probeg' 
        THEN ap.ap_talk_secs + ap.ap_acw_secs + ap.ap_ring_secs + ap.ap_hold_secs
        ELSE ap.ap_talk_secs + ap.ap_acw_secs + ap.ap_hold_secs
    END AS ap_tht,

    -- LOGIN COUNT
    CASE
        WHEN COUNT(k.agent_email) OVER (PARTITION BY k.report_date, k.agent_email) > 1
        THEN ap.ap_ready_secs::numeric / 28800
        ELSE 1
    END AS login_count,

    -- session 
    COALESCE(ses.ses_sessions,0) ses_sessions, 
    COALESCE(ses.ses_ready_secs,0) ses_ready_secs, 
    COALESCE(ses.ses_break_secs,0) ses_break_secs,

    -- agent-DAY login/logout windowed to day
    MIN(ses.ses_min_login)  OVER (PARTITION BY k.report_date, k.agent_email) AS day_first_login,
    MAX(ses.ses_max_logout) OVER (PARTITION BY k.report_date, k.agent_email) AS day_last_logout

FROM keys k
LEFT JOIN ap
    ON ap.report_date = k.report_date AND ap.agent_email = k.agent_email AND ap.campaign_name = k.campaign_name
LEFT JOIN ch  
    ON ch.report_date = k.report_date AND ch.agent_email = k.agent_email AND ch.campaign_name = k.campaign_name
LEFT JOIN ses 
    ON ses.report_date = k.report_date AND ses.agent_email = k.agent_email AND ses.campaign_name = k.campaign_name
LEFT JOIN mt
    ON mt.report_date = k.report_date AND mt.agent_email = k.agent_email;


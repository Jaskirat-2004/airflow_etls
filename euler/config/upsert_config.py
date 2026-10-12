# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS
# LAST_DATE : 2026-09-09

JS_TEMP_TABLES= [
    "roster_staging",
    "agent_mapper_staging",
    "downtime_login_hr_staging",
    "sql_manual_staging",
    "agent_productivity_interval_summary_staging",
    "head_count_staging",
    "agent_session_details_staging",
    "leads_manual_staging",
    "call_history_staging"
]


# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_TEMP_CONFIG = {

    "roster_staging": {
        "primary_key": ["report_date", "emp_id"],
        "destination_table": "roster"
    },

    "agent_mapper_staging": {
        "primary_key": ["email_id","emp_id"],
        "destination_table": "agent_mapper"
    },

    "downtime_login_hr_staging": {
        "primary_key": ["report_date", "emp_id", "reason"],
        "destination_table": "downtime_login_hr"
    },

    "sql_manual_staging": {
        "primary_key": ["report_date", "user_id"],
        "destination_table": "sql_manual"
    },

    # interval_start is deliberately NOT in this key - Euler's APSI is a daily
    # roll-up so it adds no discrimination, and it is one of the columns hit by
    # the Aug 1-12 date flip.
    "agent_productivity_interval_summary_staging": {
        "primary_key": ["report_date", "campaign_name", "user_id"],
        "destination_table": "agent_productivity_interval_summary"
    },

    "head_count_staging": {
        "primary_key": ["report_date", "employee_id"],
        "destination_table": "head_count"
    },

    "agent_session_details_staging": {
        "primary_key": ["report_date", "user_id", "session_id", "auto_call_on_off_history_id"],
        "destination_table": "agent_session_details"
    },

    "leads_manual_staging": {
        "primary_key": ["report_date", "phone"],
        "destination_table": "leads_manual"
    },

    # backed by UNIQUE NULLS NOT DISTINCT, not a PK - these 3 columns are NULL
    # on ~1.55M unattended dialer rows.
    "call_history_staging": {
        "primary_key": ["report_date", "call_id", "user_id",
                        "disposition_code", "disposition_class"],
        "destination_table": "call_history"
    },

}

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_TEMP_TABLES= [
    "roster_staging",
    "head_count_staging",
    "downtime_login_hr_staging",
    "acd_call_details_staging",
    "acd_call_interval_summary_staging",
    "agent_productivity_interval_summary_staging",
    "agent_session_details_staging",
    "ivr_footprint_staging",
    "call_details_staging",
    "forecast_staging"
]


# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_TEMP_CONFIG = {

    "roster_staging": {
        "primary_key": ["report_date", "emp_id"],
        "destination_table": "roster"
    },

    "head_count_staging": {
        "primary_key": ["report_date", "employee_id"],
        "destination_table": "head_count"
    },

    "downtime_login_hr_staging": {
        "primary_key": ["report_date", "emp_id"],
        "destination_table": "downtime_login_hr"
    },

    "acd_call_details_staging": {
        "primary_key": ["report_date", "call_id"],
        "destination_table": "acd_call_details"
    },

    "acd_call_interval_summary_staging": {
        "primary_key": ["report_date", "interval_start", "queue_name"],
        "destination_table": "acd_call_interval_summary"
    },

    "agent_productivity_interval_summary_staging": {
        "primary_key": ["report_date", "interval_start", "campaign_name", "user_id"],
        "destination_table": "agent_productivity_interval_summary"
    },

    "agent_session_details_staging": {
        "primary_key": ["report_date", "user_id", "session_id", "auto_call_on_off_history_id"],
        "destination_table": "agent_session_details"
    },

    "ivr_footprint_staging": {
        "primary_key": ["report_date", "call_id"],
        "destination_table": "ivr_footprint"
    },

    "call_details_staging": {
        "primary_key": ["report_date", "call_id"],
        "destination_table": "call_details"
    },

    "forecast_staging": {
        "primary_key": ["report_date",],
        "destination_table": "forecast"
    },

}
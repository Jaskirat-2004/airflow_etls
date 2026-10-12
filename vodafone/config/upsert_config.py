# JS ============================================================ JS
#                       VODAFONE UPSERT CONFIG
# JS ============================================================ JS
#
# JS ---------------------------------------------------------------- JS
#  DELIBERATELY NOT IN THIS CONFIG - both stay direct-load, no staging, no PK:
#
#   custom_pool_report
#   custom_tagging
# JS ---------------------------------------------------------------- JS


# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_TEMP_TABLES = [
    "city_mapper_staging",
    "roster_staging",
    "downtime_login_hr_staging",
    "head_count_staging",
    "custom_agent_productivity_interval_summary_staging",
    "agent_productivity_interval_summary_staging",
    "pc_collated_dump_staging",
    "agent_session_details_staging",
    "acd_call_details_staging",
    "acd_call_interval_summary_staging",
    "lead_master_staging",
]


# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_TEMP_CONFIG = {

    "city_mapper_staging": {
        "primary_key": ["old_circle_code"],
        "destination_table": "city_mapper"
    },

    "roster_staging": {
        "primary_key": ["report_date", "emp_id"],
        "destination_table": "roster"
    },

    "downtime_login_hr_staging": {
        "primary_key": ["report_date", "emp_id", "reason"],
        "destination_table": "downtime_login_hr"
    },

    "head_count_staging": {
        "primary_key": ["report_date", "employee_id"],
        "destination_table": "head_count"
    },

    "custom_agent_productivity_interval_summary_staging": {
        "primary_key": ["report_date", "interval_start", "campaign_name", "user_id"],
        "destination_table": "custom_agent_productivity_interval_summary"
    },

    "agent_productivity_interval_summary_staging": {
        "primary_key": ["report_date", "interval_start", "campaign_name", "user_id"],
        "destination_table": "agent_productivity_interval_summary"
    },

    "pc_collated_dump_staging": {
        "primary_key": ["report_date", "activity_id"],
        "destination_table": "pc_collated_dump"
    },

    "agent_session_details_staging": {
        "primary_key": ["report_date", "user_id", "session_id", "auto_call_on_off_history_id"],
        "destination_table": "agent_session_details"
    },

    "acd_call_details_staging": {
        "primary_key": ["report_date", "call_id"],
        "destination_table": "acd_call_details"
    },

    "acd_call_interval_summary_staging": {
        "primary_key": ["report_date", "interval_start", "queue_name"],
        "destination_table": "acd_call_interval_summary"
    },

    "lead_master_staging": {
        "primary_key": ["report_date", "lead_number"],
        "destination_table": "lead_master",
        "prune_null_date": True
    },

}

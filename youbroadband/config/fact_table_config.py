# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS

from youbroadband.config.call_details_config import (YOUBROADBAND_FACT_CALL_DETAILS_REPORT_DDL,YOUBROADBAND_FACT_CALL_DETAILS_REPORT_QUERY)
from youbroadband.config.ivr_config import (YOUBROADBAND_FACT_IVR_REPORT_DDL,YOUBROADBAND_FACT_IVR_REPORT_QUERY)
from youbroadband.config.dpd_config import (YOUBROADBAND_FACT_DPD_REPORT_DDL,YOUBROADBAND_FACT_DPD_REPORT_QUERY)
from youbroadband.config.attendance_config import (YOUBROADBAND_FACT_ATTENDANCE_REPORT_DDL,YOUBROADBAND_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_FACT_TABLES= [
    "youbroadband_fact_call_details_report",
    "youbroadband_fact_ivr_report",
    "youbroadband_fact_dpd_report",
]

JS_FACT_TABLES_CREATE= [
    "youbroadband_fact_call_details_report",
    "youbroadband_fact_ivr_report",
    "youbroadband_fact_dpd_report",
    "youbroadband_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    "youbroadband_fact_dpd_report" : {
        "query" : YOUBROADBAND_FACT_DPD_REPORT_QUERY,
        "ddl" : YOUBROADBAND_FACT_DPD_REPORT_DDL,
        "destination_table" : "youbroadband_fact_dpd_report",
        "source_tables" : [
            {"table_name" : "agent_productivity_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "acd_call_details" , "date_column" : "report_date"},
            {"table_name" : "acd_call_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "ivr_footprint" , "date_column" : "report_date"},
        ],
    },

    "youbroadband_fact_call_details_report" : {
        "query" : YOUBROADBAND_FACT_CALL_DETAILS_REPORT_QUERY,
        "ddl" : YOUBROADBAND_FACT_CALL_DETAILS_REPORT_DDL,
        "destination_table" : "youbroadband_fact_call_details_report",
        "source_tables" : [
            {"table_name" : "call_details" , "date_column" : "report_date"},
            {"table_name" : "head_count" , "date_column" : "report_date"},
        ],
    },

    "youbroadband_fact_ivr_report" : {
        "query" : YOUBROADBAND_FACT_IVR_REPORT_QUERY,
        "ddl" : YOUBROADBAND_FACT_IVR_REPORT_DDL,
        "destination_table" : "youbroadband_fact_ivr_report",
        "source_tables" : [
            {"table_name" : "ivr_footprint" , "date_column" : "report_date"},
        ],
    },

    # only for create table
    "youbroadband_fact_attendance_report" : {
        "query" : YOUBROADBAND_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : YOUBROADBAND_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "youbroadband_fact_attendance_report",
        "source_tables" : [
        ],
    },
  
}

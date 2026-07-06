# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS

from traya.config.crm_config import (TRAYA_FACT_CRM_REPORT_DDL,TRAYA_FACT_CRM_REPORT_QUERY)
from traya.config.apr_config import (TRAYA_FACT_APR_REPORT_DDL,TRAYA_FACT_APR_REPORT_QUERY)
from traya.config.aux_config import (TRAYA_FACT_AUX_REPORT_DDL,TRAYA_FACT_AUX_REPORT_QUERY)
from traya.config.inbound_config import (TRAYA_FACT_INBOUND_REPORT_DDL,TRAYA_FACT_INBOUND_REPORT_QUERY)
from traya.config.attendance_config import (TRAYA_FACT_ATTENDANCE_REPORT_DDL,TRAYA_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_FACT_TABLES= [
    "traya_fact_crm_report",
    "traya_fact_apr_report",
    "traya_fact_aux_report",
    "traya_fact_inbound_report",
]

JS_FACT_TABLES_CREATE= [
    "traya_fact_crm_report",
    "traya_fact_apr_report",
    "traya_fact_aux_report",
    "traya_fact_inbound_report",
    "traya_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    "traya_fact_crm_report" : {
        "query" : TRAYA_FACT_CRM_REPORT_QUERY,
        "ddl" : TRAYA_FACT_CRM_REPORT_DDL,
        "destination_table" : "traya_fact_crm_report",
        "source_tables" : [
            {"table_name" : "calling_kpis_data" , "date_column" : "report_date"},
            {"table_name" : "master_tracker" , "date_column" : "report_date"},
        ],
    },

    "traya_fact_apr_report" : {
        "query" : TRAYA_FACT_APR_REPORT_QUERY,
        "ddl" : TRAYA_FACT_APR_REPORT_DDL,
        "destination_table" : "traya_fact_apr_report",
        "source_tables" : [
            {"table_name" : "agent_productivity_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "call_history" , "date_column" : "report_date"},
            {"table_name" : "agent_session_details" , "date_column" : "report_date"},
            {"table_name" : "master_tracker" , "date_column" : "report_date"},
        ],
    },

    "traya_fact_aux_report" : {
        "query" : TRAYA_FACT_AUX_REPORT_QUERY,
        "ddl" : TRAYA_FACT_AUX_REPORT_DDL,
        "destination_table" : "traya_fact_aux_report",
        "source_tables" : [
            {"table_name" : "agent_session_details" , "date_column" : "report_date"},
            {"table_name" : "master_tracker" , "date_column" : "report_date"},
        ],
    },

    "traya_fact_inbound_report" : {
        "query" : TRAYA_FACT_INBOUND_REPORT_QUERY,
        "ddl" : TRAYA_FACT_INBOUND_REPORT_DDL,
        "destination_table" : "traya_fact_inbound_report",
        "source_tables" : [
            {"table_name" : "agent_productivity_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "acd_call_details" , "date_column" : "report_date"},
            {"table_name" : "master_tracker" , "date_column" : "report_date"},
        ],
    },

    # only for create table
    "traya_fact_attendance_report" : {
        "query" : TRAYA_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : TRAYA_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "traya_fact_attendance_report",
        "source_tables" : [
        ],
    },
  
}

# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS

from euler.config.connectivity_config import (EULER_FACT_CONNECTIVITY_REPORT_DDL,EULER_FACT_CONNECTIVITY_REPORT_QUERY)
from euler.config.disposition_config import (EULER_FACT_DISPOSITION_REPORT_DDL,EULER_FACT_DISPOSITION_REPORT_QUERY)
from euler.config.apr_config import (EULER_FACT_APR_REPORT_DDL, EULER_FACT_APR_REPORT_QUERY)
from euler.config.leads_config import (EULER_FACT_LEADS_REPORT_DDL, EULER_FACT_LEADS_REPORT_QUERY)
from euler.config.attendance_config import (EULER_FACT_ATTENDANCE_REPORT_DDL, EULER_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_FACT_TABLES= [
    "euler_fact_connectivity_report",
    "euler_fact_disposition_report",
    "euler_fact_apr_report",
    "euler_fact_leads_report",
]

JS_FACT_TABLES_CREATE= [
    "euler_fact_connectivity_report",
    "euler_fact_disposition_report",
    "euler_fact_apr_report",
    "euler_fact_leads_report",
    "euler_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    "euler_fact_connectivity_report" : {
        "query" : EULER_FACT_CONNECTIVITY_REPORT_QUERY,
        "ddl" : EULER_FACT_CONNECTIVITY_REPORT_DDL,
        "destination_table" : "euler_fact_connectivity_report",
        "source_tables" : [
            {"table_name" : "call_history" , "date_column" : "report_date"},
        ],
    },

    "euler_fact_disposition_report" : {
        "query" : EULER_FACT_DISPOSITION_REPORT_QUERY,
        "ddl" : EULER_FACT_DISPOSITION_REPORT_DDL,
        "destination_table" : "euler_fact_disposition_report",
        "source_tables" : [
            {"table_name" : "call_history" , "date_column" : "report_date"},
        ],
    },

    "euler_fact_apr_report" : {
        "query" : EULER_FACT_APR_REPORT_QUERY,
        "ddl" : EULER_FACT_APR_REPORT_DDL,
        "destination_table" : "euler_fact_apr_report",
        "source_tables" : [
            {"table_name" : "agent_productivity_interval_summary", "date_column" : "report_date"},
            {"table_name" : "call_history",                        "date_column" : "report_date"},
            {"table_name" : "sql_manual",                          "date_column" : "report_date"},
        ],
    },

    "euler_fact_leads_report" : {
        "query" : EULER_FACT_LEADS_REPORT_QUERY,
        "ddl" : EULER_FACT_LEADS_REPORT_DDL,
        "destination_table" : "euler_fact_leads_report",
        "source_tables" : [
            {"table_name" : "call_history",                        "date_column" : "report_date"},
            {"table_name" : "leads_unified",                       "date_column" : "report_date"},
        ],
    },

    
    # only for create table
    "euler_fact_attendance_report" : {
        "query" : EULER_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : EULER_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "euler_fact_attendance_report",
        "source_tables" : [
        ],
    },
  
}

# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS
#  LAST_DATE : 2026-09-17

from flipkart_maxicus.config.apr_config import (FLIPKART_FACT_APR_REPORT_DDL,FLIPKART_FACT_APR_REPORT_QUERY)
from flipkart_maxicus.config.hygiene_config import (FLIPKART_FACT_AGENT_HYGIENE_REPORT_DDL,FLIPKART_FACT_AGENT_HYGIENE_REPORT_QUERY)
from flipkart_maxicus.config.rr_config import (FLIPKART_FACT_RR_REPORT_DDL,FLIPKART_FACT_RR_REPORT_QUERY)
from flipkart_maxicus.config.fcr_config import (FLIPKART_FACT_FCR_REPORT_DDL,FLIPKART_FACT_FCR_REPORT_QUERY)
from flipkart_maxicus.config.attendance_config import (FLIPKART_FACT_ATTENDANCE_REPORT_DDL,FLIPKART_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_FACT_TABLES= [
    "flipkart_fact_apr_report",
    "flipkart_fact_rr_report",
    "flipkart_fact_agent_hygiene_report",

]

JS_FACT_TABLES_CREATE= [
    "flipkart_fact_apr_report",
    "flipkart_fact_rr_report",
    "flipkart_fact_agent_hygiene_report",
    "flipkart_fact_fcr_report",
    "flipkart_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    "flipkart_fact_apr_report" : {
        "query" : FLIPKART_FACT_APR_REPORT_QUERY,
        "ddl" : FLIPKART_FACT_APR_REPORT_DDL,
        "destination_table" : "flipkart_fact_apr_report",
        "source_tables" : [
            {"table_name" : "apr_dump" , "date_column" : "report_date"},
            {"table_name" : "head_count" , "date_column" : "report_date"},
        ],
    },

    "flipkart_fact_rr_report" : {
        "query" : FLIPKART_FACT_RR_REPORT_QUERY,
        "ddl" : FLIPKART_FACT_RR_REPORT_DDL,
        "destination_table" : "flipkart_fact_rr_report",
        "source_tables" : [
            {"table_name" : "rr_dump" , "date_column" : "report_date"},
            {"table_name" : "head_count" , "date_column" : "report_date"},
        ],
    },

    "flipkart_fact_agent_hygiene_report" : {
        "query" : FLIPKART_FACT_AGENT_HYGIENE_REPORT_QUERY,
        "ddl" : FLIPKART_FACT_AGENT_HYGIENE_REPORT_DDL,
        "destination_table" : "flipkart_fact_agent_hygiene_report",
        "source_tables" : [
            {"table_name" : "echi_dump" , "date_column" : "report_date"},
        ],
    },

    # only for create table
    "flipkart_fact_attendance_report" : {
        "query" : FLIPKART_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : FLIPKART_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "flipkart_fact_attendance_report",
        "source_tables" : [
        ],
    },

    "flipkart_fact_fcr_report" : {
        "query" : FLIPKART_FACT_FCR_REPORT_QUERY,
        "ddl" : FLIPKART_FACT_FCR_REPORT_DDL,
        "destination_table" : "flipkart_fact_fcr_report",
        "source_tables" : [
        ],
    },
  
}

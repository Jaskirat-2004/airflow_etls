# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS

from platinumrx.config.attendance_config import (PLATINUMRX_FACT_ATTENDANCE_REPORT_DDL,PLATINUMRX_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

# NOTE : the APR / FTE / PC-COLLATED / LEADS / INBOUND facts are NOT built for PLATINUMRX yet.
#        Their VODAFONE originals are parked in _vodafone_reference/ until the feeds land.
#        Until then this list is empty and platinumrx_fact_table_etl has no tables to load.

JS_FACT_TABLES= [
]

JS_FACT_TABLES_CREATE= [
    "platinumrx_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    # attendance runs on its own DAG (45 day rolling reload window)
    "platinumrx_fact_attendance_report" : {
        "query" : PLATINUMRX_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : PLATINUMRX_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "platinumrx_fact_attendance_report",
        "source_tables" : [
            {"table_name" : "platinumrx_head_count" , "date_column" : "report_date"},
            {"table_name" : "platinumrx_roster" , "date_column" : "report_date"},
            {"table_name" : "platinumrx_agent_login" , "date_column" : "report_date"},
        ],
    },

}

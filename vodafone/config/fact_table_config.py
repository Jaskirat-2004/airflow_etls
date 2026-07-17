# JS ============================================================ JS
#                         IMPORTING QUERIES
# JS ============================================================ JS

from vodafone.config.apr_config import (VODAFONE_FACT_APR_REPORT_DDL,VODAFONE_FACT_APR_REPORT_QUERY)
from vodafone.config.fte_config import (VODAFONE_FACT_FTE_REPORT_DDL,VODAFONE_FACT_FTE_REPORT_QUERY)
from vodafone.config.pc_collated_config import (VODAFONE_FACT_PC_COLLATED_REPORT_DDL,VODAFONE_FACT_PC_COLLATED_REPORT_QUERY)
from vodafone.config.leads_config import (VODAFONE_FACT_LEADS_REPORT_DDL,VODAFONE_FACT_LEADS_REPORT_QUERY)
# from vodafone.config.inbound_config import (VODAFONE_FACT_INBOUND_REPORT_DDL,VODAFONE_FACT_INBOUND_REPORT_QUERY)
from vodafone.config.attendance_config import (VODAFONE_FACT_ATTENDANCE_REPORT_DDL,VODAFONE_FACT_ATTENDANCE_REPORT_QUERY)

# JS ============================================================ JS
#                           TABLE NAMES
# JS ============================================================ JS

JS_FACT_TABLES= [
    "vodafone_fact_apr_report",
    "vodafone_fact_fte_report",
    "vodafone_fact_pc_collated_report",
    "vodafone_fact_leads_report",
    # "vodafone_fact_inbound_report",
]

JS_FACT_TABLES_CREATE= [
    "vodafone_fact_apr_report",
    "vodafone_fact_fte_report",
    "vodafone_fact_pc_collated_report",
    "vodafone_fact_leads_report",
    # "vodafone_fact_inbound_report",
    "vodafone_fact_attendance_report",
]

# JS ============================================================= JS
#                       THIS IS THE MAIN CONFIG
# JS ============================================================= JS

JS_FACT_CONFIG = {

    "vodafone_fact_apr_report" : {
        "query" : VODAFONE_FACT_APR_REPORT_QUERY,
        "ddl" : VODAFONE_FACT_APR_REPORT_DDL,
        "destination_table" : "vodafone_fact_apr_report",
        "source_tables" : [
            {"table_name" : "custom_agent_productivity_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "vodafone_head_count" , "date_column" : "report_date"},
        ],
    },

    "vodafone_fact_fte_report" : {
        "query" : VODAFONE_FACT_FTE_REPORT_QUERY,
        "ddl" : VODAFONE_FACT_FTE_REPORT_DDL,
        "destination_table" : "vodafone_fact_fte_report",
        "source_tables" : [
            {"table_name" : "agent_productivity_interval_summary" , "date_column" : "report_date"},
            {"table_name" : "vodafone_head_count" , "date_column" : "report_date"},
        ],
    },

    "vodafone_fact_pc_collated_report" : {
        "query" : VODAFONE_FACT_PC_COLLATED_REPORT_QUERY,
        "ddl" : VODAFONE_FACT_PC_COLLATED_REPORT_DDL,
        "destination_table" : "vodafone_fact_pc_collated_report",
        "source_tables" : [
            {"table_name" : "pc_collated_dump" , "date_column" : "report_date"},
        ],
    },

    "vodafone_fact_leads_report" : {
        "query" : VODAFONE_FACT_LEADS_REPORT_QUERY,
        "ddl" : VODAFONE_FACT_LEADS_REPORT_DDL,
        "destination_table" : "vodafone_fact_leads_report",
        "source_tables" : [
            {"table_name" : "lead_master" , "date_column" : "report_date"},
        ],
    },

    # "vodafone_fact_inbound_report" : {
    #     "query" : VODAFONE_FACT_INBOUND_REPORT_QUERY,
    #     "ddl" : VODAFONE_FACT_INBOUND_REPORT_DDL,
    #     "destination_table" : "vodafone_fact_inbound_report",
    #     "source_tables" : [
    #         {"table_name" : "agent_productivity_interval_summary" , "date_column" : "report_date"},
    #         {"table_name" : "acd_call_details" , "date_column" : "report_date"},
    #         {"table_name" : "master_tracker" , "date_column" : "report_date"},
    #     ],
    # },

    # only for create table
    "vodafone_fact_attendance_report" : {
        "query" : VODAFONE_FACT_ATTENDANCE_REPORT_QUERY,
        "ddl" : VODAFONE_FACT_ATTENDANCE_REPORT_DDL,
        "destination_table" : "vodafone_fact_attendance_report",
        "source_tables" : [
        ],
    },
  
}

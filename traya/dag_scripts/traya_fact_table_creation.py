"""
PROGRAMMER : JASKIRAT
INFO : TRAYA - CREATE CLICKHOUSE FACT TABLES (idempotent, explicit DDL)
"""

# JS ========================================= IMPORTS ========================================= JS
import pendulum

from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

from traya.config.fact_table_config import JS_FACT_TABLES, JS_FACT_CONFIG

import logging
logger = logging.getLogger(__name__)

# JS ==================================== CONNECTOIN CONFIG ==================================== JS

DESTINATION_CONN_ID = "DI-CLICKHOUSE"
DESTINATION_DATABASE = "traya"

# JS ==================================== DAG ==================================== JS

default_args = {"owner": "JASKIRAT"}

@dag(
    dag_id="traya_create_fact_tables",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["traya", "fact", "creation","ddl"],
    default_args=default_args,
)
def traya_create_fact_tables():
    
    logger.info("JS ====== DAG STARTED : [traya_fact_table_creation] ===== JS")

    @task
    def create_table(table_name: str):
            
        logger.info(f"JS ====== FETCHING DETAILS : [{table_name}] ===== JS")

        config = JS_FACT_CONFIG[table_name]
        ddl = config["ddl"]
        dest_table = config["destination_table"]

        ch_conn = BaseHook.get_connection(DESTINATION_CONN_ID)
        client = Client(
            host=ch_conn.host,
            user=ch_conn.login,
            password=ch_conn.password,
        )
        logger.info(f"JS ====== CLICKHOUSE CONNECTION ESTABLISHED ===== JS")

        try:
            logger.info(f"JS ====== CREATING TABLE [{dest_table}] ====== JS")
            client.execute(ddl)
            logger.info(f"JS ====== TABLE [{dest_table}] READY ====== JS")
        except Exception as e:
            logger.error(f"JS ====== ERROR CREATING TABLE [{dest_table}] ====== JS | ERROR -> {e}")
            raise
        finally:
            client.disconnect()

    create_table.expand(table_name=JS_FACT_TABLES)

traya_create_fact_tables()
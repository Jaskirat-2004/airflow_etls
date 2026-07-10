"""
PROGRAMMER : JASKIRAT
INFO : EULER - CREATE CLICKHOUSE FACT TABLES
"""

# JS ========================================= IMPORTS ========================================= JS
import pendulum

from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

from euler.config.fact_table_config import JS_FACT_TABLES_CREATE, JS_FACT_CONFIG

import logging
logger = logging.getLogger(__name__)

# JS ==================================== CONNECTOIN CONFIG ==================================== JS

DESTINATION_CONN_ID = "DI-CLICKHOUSE"
DESTINATION_DATABASE = "eulermotors"

# JS ==================================== DAG ==================================== JS

default_args = {"owner": "JASKIRAT"}

@dag(
    dag_id="euler_create_fact_tables",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["euler", "fact", "creation","ddl"],
    default_args=default_args,
)
def euler_create_fact_tables():
    
    logger.info("JS ====== DAG STARTED : [euler_fact_table_creation] ===== JS")

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

    for fact_name in JS_FACT_TABLES_CREATE:
        create_table.override(task_id=f"create_{fact_name}")(fact_name)

euler_create_fact_tables()
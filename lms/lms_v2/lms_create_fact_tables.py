"""
PROGRAMMER : JASKIRAT
INFO : LMS DAG FOR FACT TABLE CREATION
"""

from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup

import pendulum

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

import logging

from lms.config.fact_config import FACT_TABLES, FACT_CONFIG

from lms.utils.basic_utils import ensure_clickhouse_table_from_query

# ==================== LOGGER ====================

logger = logging.getLogger(__name__)

# ==================== CONNECTION CONFIG ====================

#POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE_NAME = "lms"

#CLICKHOUSE
DESTINATION_CONN_ID = "DI-CLICKHOUSE" 
DESTINATION_DATABASE = "lms"   

# ===============================================================================
# DAG
# ===============================================================================

default_args ={
    "owner": "JASKIRAT",
}

@dag(
    dag_id="lms_create_fact_tables",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=6,
    tags=["lms", "etl", "fact"],
    default_args=default_args,
)
def lms_create_fact_tables():

    logger.info(f"J====== STARTING DAG: [lms_create_fact_tables] ======S")

    @task
    def process_fact_table(fact_table_name: str):

        logger.info(f"J====== CREATING TABLE: [{fact_table_name}]  ======S")

        config = FACT_CONFIG[fact_table_name]
        query = config["query"]
        dest_table_name = config["destination_table"]

        # ===================== CONNECTIONS =====================
        try:
            # POSTGRES CONNECTION
            pg_hook = PostgresHook(
                postgres_conn_id=SOURCE_CONN_ID,
                database=SOURCE_DATABASE_NAME
            )
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()
            logger.info("J====== Postgres connection established ======S")

            # CLICKHOUSE CONNECTION
            ch_conn = BaseHook.get_connection(DESTINATION_CONN_ID)
            client = Client(
                host=ch_conn.host,
                user=ch_conn.login,
                password=ch_conn.password
            )
            logger.info("J====== Clickhouse connection established ======S")

        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        else:
            # ==================== CREATING TABLE ====================

            ensure_clickhouse_table_from_query(
                ch_client = client,
                pg_cursor = pg_cursor,
                postgres_query = query,
                ch_database_name = DESTINATION_DATABASE,
                table_name = dest_table_name,
                order_by_column = "tuple()"
                )

        finally:
            # ===================== CLOSE CONNECTIONS =====================
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()
            if client:
                client.disconnect()
            logger.info("J====== CONNECTIONS CLOSED SUCCESSFULLY ======S")

    # ==================== STARTING TASKS ====================

    process_fact_table.expand(fact_table_name=FACT_TABLES)

lms_create_fact_tables()


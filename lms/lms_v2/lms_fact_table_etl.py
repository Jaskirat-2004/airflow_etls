"""
PROGRAMMER : JASKIRAT
INFO : LMS ETL FOR FACT TABLES
"""

from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup

import pendulum

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

import logging

from lms.config.fact_config import FACT_TABLES, FACT_CONFIG

# ==================== LOGGER ====================

logger = logging.getLogger(__name__)

# ==================== CONNECTION CONFIG ====================

# MODE = "python" or "direct"
MODE = "python"  

#POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE_NAME = "lms"

#CLICKHOUSE
DESTINATION_CONN_ID = "DI-CLICKHOUSE" 
DESTINATION_DATABASE = "lms"

BATCH_SIZE = 5000

# ==================== HELPER FUNCTIONS AND QUERIES ====================

def python_insert(pg_cursor,client, query:str,dest_table:str):

    try:
        # ==================== FACT TABLE GENERATION ====================
        pg_cursor.execute(query)
        logger.info(f"J====== EXECUTED QUERY FOR TABLE: [{dest_table}] ======S")

        columns_list = [desc[0] for desc in pg_cursor.description]
        columns_sql = ", ".join(f'"{col}"' for col in columns_list)
        
    except Exception as e:
        logger.error(f"J====== ERROR EXECUTING QUERY FOR TABLE: [{dest_table}] | ERROR: {e} ======S")
        raise

    insert_query = f"""
        INSERT INTO "{DESTINATION_DATABASE}"."{dest_table}" 
        ({columns_sql})
        VALUES
    """

    try:
        total_rows = 0
        batch_count = 0

        while True:
            # ==================== INSERTING DATA INTO CLICKHOUSE ====================
            rows = pg_cursor.fetchmany(BATCH_SIZE)

            if not rows:
                break

            client.execute(insert_query,rows)

            row_count = len(rows)

            batch_count += 1
            total_rows += row_count

            logger.info(f"J====== INSERTED ROWS -> [{row_count}] | BATCH -> [{batch_count}] | TOTAL ROWS -> [{total_rows}] ======S")

        logger.info(f"J====== FACT TABLE INSERTED SUCCESSFULLY -> [{dest_table}] | TOTAL ROWS -> [{total_rows}] ======S")

        if total_rows == 0:
            logger.warning(f"J====== NO DATA FOUND FOR TABLE: [{dest_table}] ======S")
            
    except Exception as e:
        logger.error(f"J====== ERROR MIGRATING DATA TO CLICKHOUSE: {e} ======S")
        raise


def direct_insert(pg_conn,client,query:str,dest_table:str):

    # ==================== GETTING POSTGRES CONNECTION DETAILS ====================
    port = pg_conn.port
    host = pg_conn.host
    user = pg_conn.user
    password = pg_conn.password

    insert_query = f"""
        INSERT INTO "{DESTINATION_DATABASE}"."{dest_table}"
            SELECT *
                FROM postgresql(
                    '{host}:{port}',
                    '{SOURCE_DATABASE_NAME}',
                    '$$ {query} $$',
                    '{user}',
                    '{password}'
                )
    """
    client.execute(insert_query)

    logger.info(f"J====== FACT TABLE INSERTED SUCCESSFULLY -> [{dest_table}] ======S")

# ===============================================================================
# DAG
# ===============================================================================

default_args ={
    "owner": "JASKIRAT",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=1),
}

@dag(
    dag_id="lms_fact_table_etl",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=6,
    tags=["lms", "etl", "fact"],
    default_args=default_args,
)
def lms_fact_table_etl():

    logger.info(f"J====== STARTING DAG: [lms_fact_table_etl] ======S")

    @task
    def process_fact_table(fact_table_name: str):

        logger.info(f"J====== STARTING TABLE: [{fact_table_name}]  ======S")

        config = FACT_CONFIG[fact_table_name]
        query = config["query"]
        dest_table = config["destination_table"]

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
            # ===================== TRUNCATE DESTINATION TABLE =====================
            logger.info(f"J====== TRUNCATING DESTINATION TABLE: [{dest_table}] ======S")
            client.execute(f"TRUNCATE TABLE {DESTINATION_DATABASE}.{dest_table}")
            logger.info(f"J====== DESTINATION TABLE TRUNCATED SUCCESSFULLY ======S")

            if MODE == "direct":
                direct_insert(pg_conn,client,query,dest_table)
            else:
                python_insert(pg_cursor,client,query,dest_table)

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

lms_fact_table_etl()


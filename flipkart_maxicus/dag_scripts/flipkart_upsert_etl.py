"""
PROGRAMMER : JASKIRAT 
INFO : FLIPKART UPSERT DAG
"""

# JS ================================== IMPORTS ================================== JS

import pendulum

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag,task
from airflow.providers.postgres.hooks.postgres import PostgresHook

from flipkart_maxicus.config.upsert_config import JS_TEMP_TABLES, JS_TEMP_CONFIG
from flipkart_maxicus.util.flipkart_util import upsert_query

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE = "flipkart_maxicus"

# JS ================================== DAG ================================== JS

default_args = {
    "owner" : "JASKIRAT",
}

@dag(
    dag_id="flipkart_upsert_etl",
    start_date=pendulum.datetime(2026,1,1),
    catchup=False,
    schedule = None,
    tags=["flipkart","upsert","staging"],
    default_args=default_args,
)
def upsert_dag():
    logger.info("JS ====== DAG STARTED : [flipkart_upsert_etl] ===== JS")

    @task
    def upsert(table_name):
        logger.info(f"JS ====== UPSERT STARTED : [{table_name}] ===== JS")

        # JS ========================== CONNETIONS ========================== JS
        pg_conn = pg_cursor = None
        try:
            pg_hook = PostgresHook(postgres_conn_id=SOURCE_CONN_ID,database=SOURCE_DATABASE)
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()

            logger.info("JS ====== POSTGRES CONNECTION ESTABLISHED ===== JS")
        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        else:
            # JS ========================== PARAMETRS ========================== JS

            CONFIG = JS_TEMP_CONFIG[table_name]
            primary_key = CONFIG["primary_key"]
            destination_table = CONFIG["destination_table"]
            # COLUMNS
            pg_cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                (table_name,)
            )
            columns = [r[0] for r in pg_cursor.fetchall()]
            if not columns:
                logger.info(f"JS ====== NO COLUMNS FOUND FOR -> [{table_name}] ====== JS")
                raise

            # JS ========================== UPSERT AND TRUNCATE ========================== JS
            
            query = upsert_query(table_name,destination_table,primary_key,columns) 

            try:
                # UPSERT
                pg_cursor.execute(query)
                rows = pg_cursor.rowcount
                # TRUNCATE
                pg_cursor.execute(f"TRUNCATE TABLE {table_name}")

                pg_conn.commit()
                logger.info(f"JS ====== UPSERT AND TRUNCATE COMPLETE FOR -> [{table_name}] | ROWS MERGED [{rows}] ====== JS")

            except Exception as e:
                logger.error(f"JS ====== UPSERT AND TRUNCATE FAILED FOR -> [{table_name}] | ERROR -> {e} ====== JS")
                raise

        finally:
            if pg_cursor is not None:
                pg_cursor.close()
            if pg_conn is not None:
                pg_conn.close()
                
    # ==================== STARTING TASKS ====================
    for table in JS_TEMP_TABLES:
        upsert.override(task_id=f"upsert_{table[:-8]}")(table)

upsert_dag()
"""
PROGRAMMER : JASKIRAT 
INFO : EULER ATTENDENCE FACT TABLE ETL 
"""
# JS ================================== IMPORTS ================================== JS

import pendulum 

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag, task

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

from euler.config.fact_table_config import JS_FACT_CONFIG

from euler.util.euler_util import (
    delete_forward_window,
    data_insert,
)

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE = "eulermotors"

# CLICKHOUSE
DESTINATION_CONN_ID = "DI-CLICKHOUSE"
DESTINATION_DATABASE = "eulermotors"

# TABLE LIST
JS_FACT_TABLES = ["euler_fact_attendance_report"]

# WINDOW
WINDOW = 45

# JS ================================== DAG ================================== JS

default_args = {
    "owner" : "JASKIRAT",
    "retries" : 1,
    "retry_delay" : pendulum.duration(minutes=1) 
}

@dag(
    dag_id="euler_fact_attendance_etl",
    start_date=pendulum.datetime(2026,1,1),
    catchup=False,
    schedule = None,
    tags=["euler","fact","attendance","report"],
    default_args=default_args,
)
def euler_fact_attendance_etl():

    logger.info("JS ====== DAG STARTED : [euler_fact_attendance_etl] ===== JS")
    
    @task
    def process_each_table(table_name:str):

        logger.info(f"JS ====== STARTING TABLE  : [{table_name}] ===== JS")

        # JS ========================== CONFIG ========================== JS

        CONFIG = JS_FACT_CONFIG[table_name]
        query = CONFIG["query"]
        dest_table_name = CONFIG["destination_table"]

        # JS ========================== CONNETIONS ========================== JS
        try:
            pg_hook = PostgresHook(postgres_conn_id=SOURCE_CONN_ID,database=SOURCE_DATABASE)
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()

            logger.info("JS ====== POSTGRES CONNECTION ESTABLISHED ===== JS")

            ch_conn = BaseHook.get_connection(DESTINATION_CONN_ID)
            client = Client(host=ch_conn.host,
                            user=ch_conn.login,
                            password=ch_conn.password)
            logger.info("JS ====== CLICKHOUSE CONNECTION ESTABLISHED ===== JS")

        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        else:

            try:
                # JS ========================== GET WINDOW AND DELETE FORWARD WINDOW ========================== JS
                today_date = pendulum.now().date()
                rolling_window_date = today_date.subtract(days=WINDOW).to_date_string()

                last_processed_date = rolling_window_date
                delete_forward_window(client,DESTINATION_DATABASE,dest_table_name,last_processed_date)

                # JS ========================== INSERT DATA ========================== JS
                final_query = query.format(last_processed=last_processed_date)
                total_rows = data_insert(pg_cursor,client,DESTINATION_DATABASE,dest_table_name,final_query)

                logger.info(f"JS ====== ETL COMPLETED FOR [{table_name}] | ROWS INSERTED [{total_rows}] ====== JS")

            except Exception as e:
                logger.error(f"JS ====== ETL FAILED FOR [{table_name}] | ERROR -> {e} ====== JS")
                raise

        finally:
            if pg_cursor is not None:
                pg_cursor.close()
            if pg_conn is not None:
                pg_conn.close()
            if client is not None:
                client.disconnect()
            logger.info("JS ====== CONNECTIONS CLOSED ====== JS")

    # ==================== STARTING TASKS ====================
    for fact_name in JS_FACT_TABLES:
        process_each_table.override(task_id=f"load_{fact_name}")(fact_name)

euler_fact_attendance_etl()




"""
PROGRAMMER : JASKIRAT
INFO : PLATINUMRX ATTENDENCE FACT TABLE ETL
"""
# JS ================================== IMPORTS ================================== JS

import pendulum

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag, task

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

from platinumrx.config.fact_table_config import JS_FACT_CONFIG

from platinumrx.util.platinumrx_util import (
    get_high_watermark,
    delete_forward_window,
    data_insert,
)

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE = "platinumrx"

# CLICKHOUSE
DESTINATION_CONN_ID = "DI-CLICKHOUSE"
DESTINATION_DATABASE = "platinumrx"

# TABLE LIST
JS_FACT_TABLES = ["platinumrx_fact_attendance_report"]

# WINDOW
WINDOW = 45

# JS ================================== DAG ================================== JS

default_args = {
    "owner" : "JASKIRAT",
    "retries" : 1,
    "retry_delay" : pendulum.duration(minutes=1)
}

@dag(
    dag_id="platinumrx_fact_attendance_etl",
    start_date=pendulum.datetime(2026,1,1),
    catchup=False,
    schedule = None,
    tags=["platinumrx","fact","attendance","report"],
    default_args=default_args,
)
def platinumrx_fact_attendance_etl():

    logger.info("JS ====== DAG STARTED : [platinumrx_fact_attendance_etl] ===== JS")

    @task
    def process_each_table(table_name:str):

        logger.info(f"JS ====== STARTING TABLE  : [{table_name}] ===== JS")

        # JS ========================== CONFIG ========================== JS

        CONFIG = JS_FACT_CONFIG[table_name]
        query = CONFIG["query"]
        dest_table_name = CONFIG["destination_table"]
        source_tables = CONFIG["source_tables"]

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

                # upper bound : the last date every source table actually has data for
                high_watermark = get_high_watermark(pg_cursor,source_tables)

                if high_watermark is None:
                    logger.info(f"JS ====== NO SOURCE DATA FOR [{table_name}], SKIPPING ====== JS")
                    return

                delete_forward_window(client,DESTINATION_DATABASE,dest_table_name,last_processed_date)

                # JS ========================== INSERT DATA ========================== JS
                final_query = query.format(last_processed=last_processed_date, high_water_mark=high_watermark)
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

platinumrx_fact_attendance_etl()




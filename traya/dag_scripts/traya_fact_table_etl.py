"""
PROGRAMMER : JASKIRAT 
INFO : TRAYA FACT TABLE ETL 
"""
# JS ================================== IMPORTS ================================== JS

import pendulum 

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag, task

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

from traya.config.fact_table_config import JS_FACT_TABLES, JS_FACT_CONFIG

from traya.util.traya_util import (
    get_high_watermark,
    get_last_processed_date,
    delete_forward_window,
    data_insert,
    update_tracking_table,
)

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE = "traya"

# CLICKHOUSE
DESTINATION_CONN_ID = "DI-CLICKHOUSE"
DESTINATION_DATABASE = "traya"

# JS ================================== DAG ================================== JS

default_args = {
    "owner" : "JASKIRAT",
    "retries" : 1,
    "retry_delay" : pendulum.duration(minutes=1) 
}

@dag(
    dag_id="traya_fact_table_etl",
    start_date=pendulum.datetime(2026,1,1),
    catchup=False,
    schedule = None,
    tags=["traya","fact","crm","report"],
    default_args=default_args,
)
def traya_fact_table_etl():

    logger.info("JS ====== DAG STARTED : [traya_fact_table_etl] ===== JS")
    
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
                # JS ========================== GET WINDOW ========================== JS
                high_watermark = get_high_watermark(pg_cursor,source_tables)
                last_processed_date = get_last_processed_date(pg_cursor,table_name)

                # EARLY RETURN CHECKS
                if high_watermark is None:
                    logger.info(f"JS ====== NO SOURCE DATA FOR [{table_name}], SKIPPING ====== JS")
                    return

                if str(high_watermark) <= last_processed_date:
                    logger.info(
                        f"JS ====== NO NEW DATA FOR [{table_name}] "
                        f"(high_water_mark=[{high_watermark}] <= last_processed=[{last_processed_date}]), SKIPPING ====== JS"
                    )
                    return

                # JS ========================== DELETE FORWARD WINDOW AND INSERT ========================== JS
                delete_forward_window(client,DESTINATION_DATABASE,dest_table_name,last_processed_date)

                final_query = query.format(last_processed=last_processed_date, high_water_mark=high_watermark)
                total_rows = data_insert(pg_cursor,client,DESTINATION_DATABASE,dest_table_name,final_query)

                # JS ========================== UPDATE THE TRACKING TABLE ========================== JS
                update_tracking_table(pg_cursor,table_name,high_watermark,total_rows)

                logger.info(f"JS ====== ETL COMPLETED FOR [{table_name}] ====== JS")

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

traya_fact_table_etl()




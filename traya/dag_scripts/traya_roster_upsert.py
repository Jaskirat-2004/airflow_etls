"""
PROGRAMMER : JASKIRAT 
INFO : TRAYA ROSTER UPSERT
"""

# JS ================================== IMPORTS ================================== JS

import pendulum

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag,task
from airflow.providers.postgres.hooks.postgres import PostgresHook

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID = "DI-POSTGRES"
SOURCE_DATABASE = "traya"

# JS ================================== DAG ================================== JS

default_args = {
    "owner" : "JASKIRAT",
}

@dag(
    dag_id="traya_roster_upsert",
    start_date=pendulum.datetime(2026,1,1),
    catchup=False,
    schedule = None,
    tags=["traya","upsert","roster"],
    default_args=default_args,
)
def roster_upsert_dag():
    logger.info("JS ====== DAG STARTED : [traya_roster_upsert] ===== JS")

    @task
    def upsert():

        # JS ========================== CONNETIONS ========================== JS
        try:
            pg_hook = PostgresHook(postgres_conn_id=SOURCE_CONN_ID,database=SOURCE_DATABASE)
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()

            logger.info("JS ====== POSTGRES CONNECTION ESTABLISHED ===== JS")
        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        else:
            # JS ========================== UPSERT QUERY ========================== JS
            upsert_query = """
                INSERT INTO roster (report_date, emp_id, roster)
                SELECT report_date, emp_id, roster
                FROM roster_staging
                ON CONFLICT (report_date, emp_id)
                DO UPDATE SET
                    roster     = EXCLUDED.roster,
                    updated_at = NOW();
            """

            # JS ========================== EXECUTE QUERY ========================== JS
            try:
                pg_cursor.execute(upsert_query)
                rows = pg_cursor.rowcount
                pg_conn.commit()

                logger.info(f"JS ====== ROSTER UPSERT COMPLETE | ROWS MERGED [{rows}] ====== JS")

            except Exception as e:
                logger.error(f"JS ====== ROSTER UPSERT FAILED | ERROR -> {e} ====== JS")
                raise

        finally:
            if pg_cursor is not None:
                pg_cursor.close()
            if pg_conn is not None:
                pg_conn.close()
                
    # ==================== STARTING TASKS ====================
    upsert()

roster_upsert_dag()
"""
PROGRAMMER : JASKIRAT
INFO : TRAYA IDENTITY MAP SYNC - maintains agent_identity_map (client id -> emp_id)

Runs BEFORE traya_fact_table_etl. Append only: it never edits or deletes an
existing row, so nothing it does can change yesterday's numbers.
"""

# JS ================================== IMPORTS ================================== JS

import pendulum

import logging
logger = logging.getLogger(__name__)

from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

# JS =============================== CONNECTION CONFIG =============================== JS

# POSTGRES
SOURCE_CONN_ID  = "DI-POSTGRES"
SOURCE_DATABASE = "traya"

EMP_ID_SHAPE = r"^[0-9]{5,6}$|^NAPS[0-9]{6}$"

# JS ---- a repointed login must persist this many snapshots before we even report it
MIN_DAYS_TO_REPORT = 2

# JS ================================== DAG ================================== JS

default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id="traya_identity_map_sync",
    start_date=pendulum.datetime(2026, 1, 1),
    catchup=False,
    schedule=None,
    tags=["traya", "identity", "mapper"],
    default_args=default_args,
)
def identity_map_sync_dag():
    logger.info("JS ====== DAG STARTED : [traya_identity_map_sync] ===== JS")

    @task
    def sync_new_ids():
        """Learn client ids the crosswalk has never seen. Never touches an existing row."""

        # JS ========================== CONNECTIONS ========================== JS
        try:
            pg_hook   = PostgresHook(postgres_conn_id=SOURCE_CONN_ID, database=SOURCE_DATABASE)
            pg_conn   = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()

            logger.info("JS ====== POSTGRES CONNECTION ESTABLISHED ===== JS")
        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASE: {e} ======S")
            raise

        else:
            # JS ========================== INSERT QUERY ========================== JS
            insert_query = f"""
                INSERT INTO agent_identity_map
                    (client_id, emp_id, valid_from, valid_to, source)
                SELECT s.client_id, s.emp_id,
                       DATE '1900-01-01', DATE '9999-12-31',
                       'auto ' || current_date
                FROM (
                    SELECT lower(trim(ameyo_id)) AS client_id, emp_id
                    FROM master_tracker
                    WHERE ameyo_id IS NOT NULL AND trim(ameyo_id) NOT IN ('','-','0')
                      AND emp_id   IS NOT NULL AND trim(emp_id)   <> ''
                    GROUP BY 1,2) s
                WHERE NOT EXISTS (
                        SELECT 1 FROM agent_identity_map m
                        WHERE m.client_id = s.client_id)
                  AND s.emp_id ~ '{EMP_ID_SHAPE}';
            """

            # JS ========================== EXECUTE QUERY ========================== JS
            try:
                pg_cursor.execute(insert_query)
                rows = pg_cursor.rowcount
                pg_conn.commit()

                logger.info(f"JS ====== NEW CLIENT IDS LEARNED : {rows} ===== JS")
            except Exception as e:
                pg_conn.rollback()
                logger.error(f"J====== ERROR INSERTING NEW CLIENT IDS: {e} ======S")
                raise
            finally:
                pg_cursor.close()
                pg_conn.close()

            return rows

    @task
    def check_id_changes():
        """A login now pointing at a DIFFERENT emp_id. Reported, NEVER applied."""

        try:
            pg_hook   = PostgresHook(postgres_conn_id=SOURCE_CONN_ID, database=SOURCE_DATABASE)
            pg_conn   = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()
        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASE: {e} ======S")
            raise

        check_query = f"""
            SELECT s.client_id, m.emp_id, s.emp_id, s.first_seen, s.days_seen
            FROM (
                SELECT lower(trim(ameyo_id)) AS client_id, emp_id,
                       min(report_date)           AS first_seen,
                       count(DISTINCT report_date) AS days_seen
                FROM master_tracker
                WHERE ameyo_id IS NOT NULL AND trim(ameyo_id) NOT IN ('','-','0')
                  AND emp_id   IS NOT NULL AND trim(emp_id)   <> ''
                GROUP BY 1,2) s
            JOIN agent_identity_map m
              ON  m.client_id = s.client_id
              AND m.valid_to  = DATE '9999-12-31'
            WHERE s.emp_id <> m.emp_id
              AND s.days_seen >= {MIN_DAYS_TO_REPORT};
        """

        try:
            pg_cursor.execute(check_query)
            changes = pg_cursor.fetchall()
        except Exception as e:
            logger.error(f"J====== ERROR CHECKING ID CHANGES: {e} ======S")
            raise
        finally:
            pg_cursor.close()
            pg_conn.close()

        # JS ========================== REPORT ========================== JS
        if changes:
            logger.warning("JS ====== EMP_ID CHANGES PENDING APPROVAL ===== JS")
            for client_id, old_emp, new_emp, first_seen, days in changes:
                logger.warning(
                    f"JS ------ {client_id} : {old_emp} -> {new_emp} "
                    f"(new id first seen {first_seen}, on {days} snapshots) ------ JS")
            logger.warning(
                f"JS ====== {len(changes)} PENDING. Close the old row (valid_to), "
                f"insert the new one. See work/traya/DDL-agent-identity-map.sql ===== JS")
        else:
            logger.info("JS ====== NO EMP_ID CHANGES DETECTED ===== JS")

        return len(changes)

    # ==================== STARTING TASKS ====================
    sync_new_ids() >> check_id_changes()

identity_map_sync_dag()

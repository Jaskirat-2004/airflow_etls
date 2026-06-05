"""
PROGRAMMER : JASKIRAT
INFO : LMS ETL FOR MERGED USER X LESSON TABLE
"""

from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup

import pendulum

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

import logging

# ==================== LOGGER ====================

logger = logging.getLogger(__name__)

# ==================== CONNECTION CONFIG ====================

# True -> Create Tables | False -> Skip Table Creation
TABLE_CREATION_MODE = True 

# CLICKHOUSE CONNECTIONS
SOURCE_CONN_ID = "DI-CLICKHOUSE" 
SOURCE_DATABASE = "lms"
JOIN_DATABASE = "sampark"

BATCH_SIZE = 5000

# TABLE NAMES
SOURCE_TABLE = "lms_fact_user_x_lesson"
DESTINATION_TABLE = "lms_fact_user_x_lesson_merged"
JOIN_TABLE = "employee_fact"

# ===============================================================================
# DAG
# ===============================================================================

default_args ={
    "owner": "JASKIRAT",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=1),
}

@dag(
    dag_id="lms_fact_user_x_lesson_merged",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=6,
    tags=["lms", "etl", "fact"],
    default_args=default_args,
)
def lms_fact_user_x_lesson_merged():

    logger.info(f"J====== STARTING DAG: [lms_fact_user_x_lesson_merged] ======S")

    @task
    def process_fact_table():
        # ===================== CONNECTIONS =====================
        try:
            # CLICKHOUSE CONNECTION
            ch_conn = BaseHook.get_connection(SOURCE_CONN_ID)
            client = Client(
                host=ch_conn.host,
                user=ch_conn.login,
                password=ch_conn.password
            )
            logger.info("J====== CLICKHOUSE CONNECTION ESTABLISHED ======S")
        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        else:
            # ===================== JOIN QUERY =====================

            join_query = f"""
            SELECT
                -- ================= LMS FACT (all columns + derived) =================
                l.*,
                replaceRegexpOne(l.usermaster_username, 'k$', '') AS clean_user_id,

                -- ================= EMPLOYEE (handpicked) =================
                e.username         AS employee_username,
                e.empId            AS employee_id,
                e.firstName        AS employee_first_name,
                e.lastName         AS employee_last_name,
                e.email            AS employee_email,
                e.Process_Name     AS employee_process_name,
                e.user_type        AS employee_user_type,
                e.grade            AS employee_grade,
                e.company          AS employee_company,
                e.city_name        AS employee_city_name,
                e.DeptName         AS employee_department_name,
                e.designation_name AS employee_designation_name,
                e.emp_status       AS employee_emp_status,
                e.current_status   AS employee_current_status

            FROM {SOURCE_DATABASE}.{SOURCE_TABLE} l

            LEFT JOIN {JOIN_DATABASE}.{JOIN_TABLE} e
                ON replaceRegexpOne(l.usermaster_username, 'k$', '') = e.empId
            """

            # ===================== CREATE DESTINATION TABLE =====================
            if TABLE_CREATION_MODE:
                logger.info(f"J====== CREATING TABLE: [{DESTINATION_TABLE}] ======S")

                create_query = f"""
                CREATE TABLE IF NOT EXISTS {SOURCE_DATABASE}.{DESTINATION_TABLE}
                ENGINE = MergeTree()
                ORDER BY tuple()
                AS
                {join_query}
                LIMIT 0
                """

                client.execute(create_query)
                logger.info(f"J====== TABLE CREATED SUCCESSFULLY ======S")

            # ===================== TRUNCATE DESTINATION TABLE =====================
            logger.info(f"J====== TRUNCATING DESTINATION TABLE: [{DESTINATION_TABLE}] ======S")
            client.execute(f"TRUNCATE TABLE `{SOURCE_DATABASE}`.`{DESTINATION_TABLE}`")
            logger.info(f"J====== DESTINATION TABLE TRUNCATED SUCCESSFULLY ======S")

            # ===================== INSERT INTO DESTINATION TABLE =====================
            
            insert_query = f"""
                INSERT INTO {SOURCE_DATABASE}.{DESTINATION_TABLE}
                {join_query}
            """
            client.execute(insert_query)

            logger.info(f"J====== DATA INSERTED INTO [{DESTINATION_TABLE}] ======S")

        finally:
            # ===================== CLOSE CONNECTIONS =====================
            if client:
                client.disconnect()
            logger.info("J====== CONNECTIONS CLOSED SUCCESSFULLY ======S")

    # ==================== STARTING TASKS ====================

    process_fact_table()

lms_fact_user_x_lesson_merged()


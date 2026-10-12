# dags/lms/lms_etl.py

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

CLICKHOUSE_CONN_ID = "Clickhouse_Knowmax"
POSTGRES_CONN_ID   = "DI-POSTGRES"
DATABASE_NAME      = "lms"

TENANTS = [
    "boat",
    "orientphygital",
    "wonderchefphygital",
    "urbancompany",
    "atomberg",
    "vivophygital",
    "lenovophygital",
    "eulermotors",
    "hafele",
    "kochiva",
]

TABLES = [
    "courses",
    "CourseModule",
    "CourseLesson",
    "enrolledusers",
    "userMaster",
    "CourseTodepartment",
    "departmentTorolePolicy",
    "department",
    "CourseTodesignation",
    "BatchToCourse",
    "Batch",
    "BatchTouserMaster",
    "CourseTouserMaster",
    "CourseProgress",
    "ModuleProgress",
    "LessonProgress",
    "Certificate",
    "CertificateTolanguageMaster",
    "languageMaster",
    "designation"
]


# ─────────────────────────────────────────────────────────────────────────────
# CORE TASK FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def transfer_table(tenant_name: str, table_name: str) -> None:
    """
    Full ETL for one (tenant, table) pair:
      1. Read all rows from ClickHouse  →  tenant_name.table_name
      2. Add client_name column to every row
      3. Insert into PostgreSQL  →  table_name (appends, no duplicates)

    Called by a separate PythonOperator task for every (tenant, table) combo.
    If this table doesn't exist for this tenant, logs a warning and skips.
    """

    # ── ClickHouse connection ─────────────────────────────────────────────────
    ch_conn   = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
    ch_client = CHClient(
        host     = ch_conn.host,
        port     = ch_conn.port or 9000,
        user     = ch_conn.login,
        password = ch_conn.password or "",
    )

    # ── Check table exists for this tenant ────────────────────────────────────
    # Some tenants may not have every table — skip gracefully instead of crashing
    exists = ch_client.execute(
        """
        SELECT count()
        FROM system.tables
        WHERE database = %(db)s
          AND name     = %(tbl)s
        """,
        {"db": tenant_name, "tbl": table_name},
    )

    if not exists or exists[0][0] == 0:
        print(f"[{tenant_name}.{table_name}] Table does not exist — skipping")
        return

    # ── Read column names ─────────────────────────────────────────────────────
    # We need the column names to build the INSERT statement correctly.
    # We fetch them from system.columns rather than hardcoding anything —
    # this way the ETL works even if schemas change slightly across tenants.
    col_rows = ch_client.execute(
        """
        SELECT name
        FROM system.columns
        WHERE database = %(db)s
          AND table    = %(tbl)s
        ORDER BY position
        """,
        {"db": tenant_name, "tbl": table_name},
    )
    columns = [row[0] for row in col_rows]

    if not columns:
        print(f"[{tenant_name}.{table_name}] No columns found — skipping")
        return

    # ── Fetch all rows from ClickHouse ────────────────────────────────────────
    # Using db.TableName syntax so we don't need USE — one client reaches any DB
    rows = ch_client.execute(
        f'SELECT * FROM `{tenant_name}`.`{table_name}`'
    )

    if not rows:
        print(f"[{tenant_name}.{table_name}] No data found — skipping")
        return

    print(f"[{tenant_name}.{table_name}] Fetched {len(rows)} rows from ClickHouse")

    # ── Transform — add client_name to every row ──────────────────────────────
    # Each row from clickhouse-driver is a tuple.
    # We convert to list and append the tenant name as the last value.
    # This matches the "client_name" TEXT NOT NULL column we added in setup.
    transformed = [list(row) + [tenant_name] for row in rows]

    # ── Build INSERT statement ────────────────────────────────────────────────
    # Column list = original columns + client_name
    all_columns = columns + ["client_name"]

    # "%s" placeholders — one per column, psycopg2 fills them safely
    placeholders = ", ".join(["%s"] * len(all_columns))

    # Double-quoted column names preserve camelCase in PostgreSQL
    col_list = ", ".join(f'"{c}"' for c in all_columns)

    # ON CONFLICT DO NOTHING — safe to re-run the DAG without creating duplicates
    # If the same row already exists it is silently skipped
    # NOTE: this requires a PRIMARY KEY or UNIQUE constraint on the Postgres table
    # If you have no constraints, replace with plain INSERT INTO
    insert_sql = (
        f'INSERT INTO "{table_name}" ({col_list}) '
        f'VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )

    # ── Insert into PostgreSQL ────────────────────────────────────────────────
    pg_hook   = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID, database=DATABASE_NAME)
    pg_conn   = pg_hook.get_conn()
    pg_cursor = pg_conn.cursor()

    # executemany sends all rows in one round trip — much faster than looping execute()
    pg_cursor.executemany(insert_sql, transformed)
    pg_conn.commit()

    print(f"[{tenant_name}.{table_name}] Inserted {len(transformed)} rows into PostgreSQL")

    pg_cursor.close()
    pg_conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# DAG
# ─────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="lms_etl",
    description="ETL: fetch from all ClickHouse tenants, append into PostgreSQL",
    schedule=None, 
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_tasks=10,    # max parallel tasks across entire DAG at once
    tags=["etl", "lms"],
) as dag:

    for tenant in TENANTS:

        # TaskGroup groups all 19 table-tasks per tenant in the Airflow UI
        # Without this you'd see 190 tasks in a flat unreadable list
        with TaskGroup(group_id=tenant) as tenant_group:

            for table in TABLES:

                PythonOperator(
                    # task_id is unique within the group
                    # Airflow prefixes it automatically: boat.transfer_courses
                    task_id=f"transfer_{table}",
                    python_callable=transfer_table,
                    op_kwargs={
                        "tenant_name": tenant,
                        "table_name":  table,
                    },
                )

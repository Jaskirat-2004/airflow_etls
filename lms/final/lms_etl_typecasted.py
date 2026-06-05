# dags/lms/lms_etl.py

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient


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

# Columns that are Bool in some tenants but SMALLINT in Postgres
# Only these specific columns get cast — everything else is untouched
BOOL_COLUMNS = {
    "userMaster":     ["isMasterEntry"],
    "department":     ["isMasterEntry"],
    "designation":     ["isMasterEntry"],
}


def transfer_table(tenant_name: str, table_name: str) -> None:

    # ── ClickHouse connection ─────────────────────────────────────────────────
    ch_conn   = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
    ch_client = CHClient(
        host     = ch_conn.host,
        port     = ch_conn.port or 9000,
        user     = ch_conn.login,
        password = ch_conn.password or "",
    )

    # ── Check table exists for this tenant ────────────────────────────────────
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
    rows = ch_client.execute(
        f'SELECT * FROM `{tenant_name}`.`{table_name}`'
    )

    if not rows:
        print(f"[{tenant_name}.{table_name}] No data found — skipping")
        return

    print(f"[{tenant_name}.{table_name}] Fetched {len(rows)} rows from ClickHouse")

    # ── Transform ─────────────────────────────────────────────────────────────
    # For known bool columns — cast True/False → 1/0 only where needed
    # For everything else — pass through untouched
    bool_cols     = BOOL_COLUMNS.get(table_name, [])
    col_index_map = {col: idx for idx, col in enumerate(columns)}

    transformed = []
    for row in rows:
        row = list(row)
        for col in bool_cols:
            idx = col_index_map.get(col)
            if idx is not None and row[idx] is not None:
                row[idx] = int(row[idx])
        row.append(tenant_name)
        transformed.append(row)

    # ── Build INSERT ──────────────────────────────────────────────────────────
    all_columns  = columns + ["client_name"]
    col_list     = ", ".join(f'"{c}"' for c in all_columns)
    placeholders = ", ".join(["%s"] * len(all_columns))

    insert_sql = (
        f'INSERT INTO "{table_name}" ({col_list}) '
        f'VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )

    # ── Insert into PostgreSQL ────────────────────────────────────────────────
    pg_hook   = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID, database=DATABASE_NAME)
    pg_conn   = pg_hook.get_conn()
    pg_cursor = pg_conn.cursor()

    pg_cursor.executemany(insert_sql, transformed)
    pg_conn.commit()

    print(f"[{tenant_name}.{table_name}] Inserted {len(transformed)} rows into PostgreSQL")

    pg_cursor.close()
    pg_conn.close()


with DAG(
    dag_id="lms_etl",
    description="ETL: fetch from all ClickHouse tenants, append into PostgreSQL",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_tasks=10,
    tags=["etl", "lms"],
) as dag:

    for tenant in TENANTS:
        with TaskGroup(group_id=tenant) as tenant_group:
            for table in TABLES:
                PythonOperator(
                    task_id=f"transfer_{table}",
                    python_callable=transfer_table,
                    op_kwargs={
                        "tenant_name": tenant,
                        "table_name":  table,
                    },
                )

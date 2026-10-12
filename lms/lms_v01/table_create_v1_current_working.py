from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient


CLICKHOUSE_CONN_ID = "Clickhouse_Knowmax"
POSTGRES_CONN_ID   = "DI-POSTGRES"
DATABASE_NAME      = "lms"
SCHEMA_SOURCE_DB   = "wonderchefphygital"

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
    "designation",
]

CLICKHOUSE_TO_POSTGRES = {
    "Int8": "SMALLINT", "Int16": "SMALLINT",
    "Int32": "INTEGER", "Int64": "BIGINT",
    "Int128": "NUMERIC", "Int256": "NUMERIC",
    "UInt8": "SMALLINT", "UInt16": "INTEGER",
    "UInt32": "BIGINT", "UInt64": "NUMERIC(20,0)",
    "UInt128": "NUMERIC", "UInt256": "NUMERIC",
    "Float32": "REAL", "Float64": "DOUBLE PRECISION",
    "String": "TEXT", "FixedString": "TEXT",
    "Date": "DATE", "Date32": "DATE",
    "DateTime": "TIMESTAMP", "DateTime64": "TIMESTAMP",
    "Bool": "BOOLEAN",
    "JSON": "JSONB", "Object": "JSONB",
    "Array": "JSONB", "Map": "JSONB", "Tuple": "JSONB",
    "UUID": "UUID",
    "Decimal": "NUMERIC", "Decimal32": "NUMERIC",
    "Decimal64": "NUMERIC", "Decimal128": "NUMERIC",
    "Enum8": "TEXT", "Enum16": "TEXT",
    "IPv4": "INET", "IPv6": "INET",
}


def convert_type(ch_type: str) -> str:
    # Strip Nullable() wrapper
    if ch_type.startswith("Nullable(") and ch_type.endswith(")"):
        ch_type = ch_type[9:-1]
    # Strip LowCardinality() wrapper
    if ch_type.startswith("LowCardinality(") and ch_type.endswith(")"):
        ch_type = ch_type[15:-1]
    # Extract base type name, dropping any parameters e.g. DateTime64(3) -> DateTime64
    base_type = ch_type.split("(")[0].strip()
    return CLICKHOUSE_TO_POSTGRES.get(base_type, "TEXT")


def fetch_and_create_tables() -> None:
    """
    Single task — does everything in one shot:
      1. Connect to ClickHouse
      2. Connect to PostgreSQL
      3. For each table: read schema from CH → build CREATE TABLE → execute in PG
      4. Print summary

    No files written anywhere. Nothing stored between steps.
    """

    # ── ClickHouse connection ─────────────────────────────────────────────────
    print("Connecting to ClickHouse...")
    ch_conn   = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
    ch_client = CHClient(
        host     = ch_conn.host,
        port     = ch_conn.port or 9000,
        user     = ch_conn.login,
        password = ch_conn.password or "",
    )
    ch_client.execute("SELECT 1")
    print(f"ClickHouse OK\n")

    # ── PostgreSQL connection ─────────────────────────────────────────────────
    print("Connecting to PostgreSQL...")
    pg_hook   = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID, database=DATABASE_NAME)
    pg_conn   = pg_hook.get_conn()
    pg_cursor = pg_conn.cursor()
    print(f"PostgreSQL OK\n")

    created = []
    failed  = []

    # ── Process each table ────────────────────────────────────────────────────
    for table_name in TABLES:
        try:
            print(f"[{table_name}] Reading schema from ClickHouse...")

            # Read column definitions from ClickHouse's internal catalogue
            columns = ch_client.execute(
                """
                SELECT name, type
                FROM system.columns
                WHERE database = %(db)s
                  AND table    = %(tbl)s
                ORDER BY position
                """,
                {"db": SCHEMA_SOURCE_DB, "tbl": table_name},
            )

            if not columns:
                raise ValueError(
                    f"No columns found — check table name is exact (case-sensitive). "
                    f"Run: SHOW TABLES FROM {SCHEMA_SOURCE_DB}"
                )

            # Build column definition lines
            col_lines = []
            for col_name, ch_type in columns:
                pg_type = convert_type(ch_type)
                col_lines.append(f'    "{col_name}" {pg_type}')

            # Add tenant identifier — does not exist in ClickHouse
            col_lines.append('    "client_name" TEXT NOT NULL')

            # Assemble CREATE TABLE
            create_sql = (
                f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n'
                + ",\n".join(col_lines)
                + "\n);"
            )

            print(f"[{table_name}] Executing in PostgreSQL...")
            pg_cursor.execute(create_sql)
            pg_conn.commit()

            print(f"[{table_name}] Done ({len(columns)} columns + client_name)\n")
            created.append(table_name)

        except Exception as e:
            pg_conn.rollback()
            print(f"[{table_name}] FAILED: {e}\n")
            failed.append((table_name, str(e)))

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=" * 55)
    print(f"Created : {len(created)}/{len(TABLES)} tables")
    if failed:
        print(f"Failed  : {len(failed)} tables")
        for name, err in failed:
            print(f"  - {name}: {err}")

    # ── Verify — list what now exists in PostgreSQL ───────────────────────────
    pg_cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type   = 'BASE TABLE'
        ORDER BY table_name
    """)
    existing = [row[0] for row in pg_cursor.fetchall()]
    print(f"\nTables confirmed in PostgreSQL ({len(existing)} total):")
    for t in existing:
        print(f"  {t}")

    pg_cursor.close()
    pg_conn.close()

    # Fail the task if anything went wrong so Airflow turns it red
    if failed:
        raise Exception(f"{len(failed)} table(s) failed. Check logs above.")


# ─────────────────────────────────────────────────────────────────────────────
# DAG
# ─────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="lms_create_tables",
    description="One-time setup: create LMS tables in PostgreSQL from ClickHouse schemas",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["setup", "one-time", "lms"],
) as dag:

    PythonOperator(
        task_id="fetch_and_create_tables",
        python_callable=fetch_and_create_tables,
    )

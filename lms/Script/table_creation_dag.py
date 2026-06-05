# dags/lms/lms_create_tables.py

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as CHClient
import os
import json

CLICKHOUSE_CONN_ID = "Clickhouse_Knowmax"
POSTGRES_CONN_ID   = "DI-POSTGRES"
DATABASE_NAME      = "lms"
SCHEMA_SOURCE_DB   = "boat"

# Save the generated schemas next to the DAG file — Airflow can always write here
SCHEMAS_FILE = "/tmp/table_schemas.json"

TABLES = [
    "Batch"
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
    if ch_type.startswith("Nullable(") and ch_type.endswith(")"):
        ch_type = ch_type[9:-1]
    if ch_type.startswith("LowCardinality(") and ch_type.endswith(")"):
        ch_type = ch_type[15:-1]
    base_type = ch_type.split("(")[0].strip()
    return CLICKHOUSE_TO_POSTGRES.get(base_type, "TEXT")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — read schemas from ClickHouse, save as JSON
# ─────────────────────────────────────────────────────────────────────────────

def generate_and_save_schemas() -> None:
    """
    Reads column definitions from ClickHouse for every table in TABLES.
    Builds a clean CREATE TABLE IF NOT EXISTS statement for each one.
    Saves all statements to a JSON file — one key per table name.

    The JSON file looks like:
    {
        "courses": "CREATE TABLE IF NOT EXISTS \"courses\" (\n    \"id\" TEXT,\n    ...\n    \"client_name\" TEXT NOT NULL\n);",
        "userMaster": "CREATE TABLE IF NOT EXISTS \"userMaster\" (\n    ...\n);"
    }
    """

    print("Connecting to ClickHouse...")
    ch_conn = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
    ch_client = CHClient(
        host     = ch_conn.host,
        port     = ch_conn.port or 9000,
        user     = ch_conn.login,
        password = ch_conn.password or "",
    )
    ch_client.execute("SELECT 1")
    print(f"ClickHouse OK — reading from: {SCHEMA_SOURCE_DB}\n")

    # This dict maps table_name → CREATE TABLE statement
    # It gets saved as JSON so Task 2 (and future runs) can load it directly
    schemas = {}

    for table_name in TABLES:
        print(f"Reading: {SCHEMA_SOURCE_DB}.{table_name}")

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
            print(f"  [WARN] No columns found for '{table_name}' — skipping")
            continue

        # Build column definitions — plain strings, no inline comments
        col_lines = []
        for col_name, ch_type in columns:
            pg_type = convert_type(ch_type)
            col_lines.append(f'    "{col_name}" {pg_type}')
            print(f"  {col_name:<40} {ch_type:<35} -> {pg_type}")

        # Add the tenant identifier column
        col_lines.append('    "client_name" TEXT NOT NULL')

        # Assemble the CREATE TABLE statement
        # IF NOT EXISTS = safe to run multiple times, never destroys data
        create_sql = (
            f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n'
            + ",\n".join(col_lines)
            + "\n);"
        )

        schemas[table_name] = create_sql
        print(f"  Done: {len(columns)} columns + client_name\n")

    # Save as JSON — simple, readable, no SQL parsing issues
    with open(SCHEMAS_FILE, "w") as f:
        json.dump(schemas, f, indent=2)

    print(f"Saved {len(schemas)} table schemas to: {SCHEMAS_FILE}")
    print("Task 2 will now read this file and create the tables in PostgreSQL.")


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — load JSON, execute each CREATE TABLE in PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────

def execute_schemas_in_postgres() -> None:
    """
    Loads the JSON file saved by Task 1.
    Runs each CREATE TABLE statement individually in PostgreSQL.

    Running them one by one (not as one big string) means:
    - If one table fails you see exactly which one
    - Other tables still get created
    - No SQL parsing issues from joining statements together
    """

    if not os.path.exists(SCHEMAS_FILE):
        raise FileNotFoundError(
            f"Schemas file not found: {SCHEMAS_FILE}\n"
            f"Run Task 1 (generate_schemas) first."
        )

    with open(SCHEMAS_FILE, "r") as f:
        schemas = json.load(f)

    print(f"Loaded {len(schemas)} table schemas from: {SCHEMAS_FILE}\n")

    pg_hook   = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID, database=DATABASE_NAME)
    pg_conn   = pg_hook.get_conn()
    pg_cursor = pg_conn.cursor()

    print("PostgreSQL OK\n")

    created = []
    failed  = []

    for table_name, create_sql in schemas.items():
        try:
            print(f"Creating: {table_name}")
            print(f"  SQL: {create_sql[:80]}...")  # print first 80 chars so you can verify

            pg_cursor.execute(create_sql)
            pg_conn.commit()   # commit after each table — if one fails others are safe

            print(f"  OK\n")
            created.append(table_name)

        except Exception as e:
            pg_conn.rollback() # rollback only the failed table, not everything
            print(f"  FAILED: {e}\n")
            failed.append((table_name, str(e)))

    # Summary
    print(f"{'='*50}")
    print(f"Created : {len(created)} tables")
    print(f"Failed  : {len(failed)} tables")

    if failed:
        print("\nFailed tables:")
        for name, err in failed:
            print(f"  {name}: {err}")

    # Verify final state in Postgres
    pg_cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type   = 'BASE TABLE'
        ORDER BY table_name
    """)
    rows = pg_cursor.fetchall()
    print(f"\nTables now in PostgreSQL ({len(rows)} total):")
    for row in rows:
        print(f"  {row[0]}")

    pg_cursor.close()
    pg_conn.close()

    # If anything failed, raise so the task turns red in Airflow UI
    if failed:
        raise Exception(f"{len(failed)} tables failed to create. Check logs above.")


# ─────────────────────────────────────────────────────────────────────────────
# DAG
# ─────────────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="lms_create_tables",
    description="One-time setup: read schemas from ClickHouse, create tables in PostgreSQL",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["setup", "one-time", "lms"],
) as dag:

    t1 = PythonOperator(
        task_id="generate_schemas",
        python_callable=generate_and_save_schemas,
    )

    t2 = PythonOperator(
        task_id="create_tables_in_postgres",
        python_callable=execute_schemas_in_postgres,
    )

    t1 >> t2

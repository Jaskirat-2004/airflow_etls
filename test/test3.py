from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import io


# -----------------------
# TENANT CONFIG
# -----------------------

TENANTS = [
    {
        "db_name": "tenant-uat-oneplus",
        "tenant_name": "oneplus",
        "tenant_id": 1
    },
    {
        "db_name": "tenant-uat-samsung",
        "tenant_name": "samsung",
        "tenant_id": 2
    }
]


# -----------------------
# TABLE CONFIG
# -----------------------

TABLES = [
    "BlockedCustomer",
    "Booking",
    "Customer",
    "CustomerFootFall",
    "CustomerTimings",
    "Feedback",
    "LiveDemo",
    "LobbyTimings",
    "SlotRule",
    "User",
    "UserTimings",
    "disabledSchedules",
    "audit_logs"
]


# -----------------------
# BUILD TASK MATRIX
# -----------------------

TASK_CONFIG = [
    {"tenant": tenant, "table": table}
    for tenant in TENANTS
    for table in TABLES
]


# -----------------------
# DAG
# -----------------------

with DAG(
    dag_id="JASKIRAT-SUPER-MULTI-TENANT-CONSOLIDATION",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=10,
) as dag:

    @task
    def transfer_data(config: dict):

        tenant = config["tenant"]
        table = config["table"]

        db_name = tenant["db_name"]
        tenant_name = tenant["tenant_name"]
        tenant_id = tenant["tenant_id"]

        target_table = f"{table}_All"

        source_hook = PostgresHook(
            postgres_conn_id="phygital-uat-oneplus",
            database=db_name
        )

        target_hook = PostgresHook(
            postgres_conn_id="DI-POSTGRES",
            database = "testing_jaskirat"
        )

        source_conn = source_hook.get_conn()
        target_conn = target_hook.get_conn()

        buffer = io.StringIO()

        # -----------------------
        # 1️⃣ CREATE TABLE IF NOT EXISTS
        # -----------------------

        with target_conn.cursor() as tgt_cursor:
            tgt_cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS public."{target_table}"
                (LIKE public."{table}" INCLUDING ALL);
            """)

            tgt_cursor.execute(f"""
                ALTER TABLE public."{target_table}"
                ADD COLUMN IF NOT EXISTS source_db TEXT,
                ADD COLUMN IF NOT EXISTS source_db_id INTEGER;
            """)

            target_conn.commit()

        # -----------------------
        # 2️⃣ GET SOURCE COLUMN ORDER
        # -----------------------

        with source_conn.cursor() as src_cursor:

            src_cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)

            source_columns = [row[0] for row in src_cursor.fetchall()]
            source_column_list = ", ".join(
                [f'"{col}"' for col in source_columns]
            )

            # -----------------------
            # 3️⃣ EXTRACT WITH FIXED ORDER
            # -----------------------

            src_cursor.copy_expert(
                f"""
                COPY (
                    SELECT {source_column_list},
                           '{tenant_name}' AS source_db,
                           {tenant_id} AS source_db_id
                    FROM public."{table}"
                )
                TO STDOUT WITH CSV
                """,
                buffer
            )

        buffer.seek(0)

        # -----------------------
        # 4️⃣ GET TARGET COLUMN ORDER
        # -----------------------

        with target_conn.cursor() as tgt_cursor:

            tgt_cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{target_table}'
                ORDER BY ordinal_position
            """)

            target_columns = [row[0] for row in tgt_cursor.fetchall()]
            target_column_list = ", ".join(
                [f'"{col}"' for col in target_columns]
            )

            # -----------------------
            # 5️⃣ LOAD SAFELY
            # -----------------------

            tgt_cursor.copy_expert(
                f"""
                COPY public."{target_table}" ({target_column_list})
                FROM STDIN WITH CSV
                """,
                buffer
            )

            target_conn.commit()

        source_conn.close()
        target_conn.close()


    transfer_data.expand(config=TASK_CONFIG)

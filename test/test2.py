from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import io

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


with DAG(
    dag_id="JASKIRAT-ALL-TABLE-COPY",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
) as dag:

    @task
    def create_table():

        target_hook = PostgresHook(postgres_conn_id="DI-POSTGRES",database = "testing_jaskirat")
        target_conn = target_hook.get_conn()

        with target_conn.cursor() as tgt_cursor:
            tgt_cursor.execute("""
                CREATE TABLE IF NOT EXISTS public."Attachments_All" (
                    id INTEGER,
                    "meetingId" TEXT,
                    "customerId" INTEGER,
                    "files" JSONB,
                    "userId" INTEGER,
                    source_db TEXT,
                    source_db_id INTEGER
                );
            """)
            target_conn.commit()


    @task
    def transfer_data(tenants:dict):

        db_name = tenants['db_name']
        tenant_name = tenants['tenant_name']
        tenant_id = tenants['tenant_id']

        source_hook = PostgresHook(
            postgres_conn_id="phygital-uat-oneplus",
            database=db_name
        )
        target_hook = PostgresHook(postgres_conn_id="DI-POSTGRES",database = "testing_jaskirat")

        source_conn = source_hook.get_conn()
        target_conn = target_hook.get_conn()

        buffer = io.StringIO()

        # Extract from source DB
        with source_conn.cursor() as src_cursor:
            src_cursor.copy_expert(
                f"""
                COPY (
                    SELECT 
                        id,
                        "meetingId",
                        "customerId",
                        "files",
                        "userId",
                        '{tenant_name}' AS source_db,
                        '{tenant_id}' AS source_db_id
                        
                    FROM public."Attachments"
                )
                TO STDOUT WITH CSV
                """,
                buffer
            )

        buffer.seek(0)

        # Append into target table
        with target_conn.cursor() as tgt_cursor:
            tgt_cursor.copy_expert(
                """
                COPY public."Attachments_All"
                (id, "meetingId", "customerId", "files", "userId", source_db,source_db_id)
                FROM STDIN WITH CSV
                """,
                buffer
            )
            target_conn.commit()

        source_conn.close()
        target_conn.close()

    table = create_table()
    transfer_tasks = transfer_data.expand(
        tenants = TENANTS
    )

    table >> transfer_tasks

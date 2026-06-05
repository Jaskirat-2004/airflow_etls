from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import io


with DAG(
    dag_id="pg_simple_copy",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
) as dag:


    @task
    def transfer():

        source_hook = PostgresHook(postgres_conn_id="phygital-uat-oneplus")
        target_hook = PostgresHook(postgres_conn_id="DI-Postgres")

        source_conn = source_hook.get_conn()
        target_conn = target_hook.get_conn()

        buffer = io.StringIO()

        # Extract from source
        with source_conn.cursor() as src_cursor:
            src_cursor.copy_expert(
                """
                COPY (
                    SELECT id, "meetingId", "customerId","files","userId"
                    FROM "Attachments"
                )
                TO STDOUT WITH CSV
                """,
                buffer
            )

        buffer.seek(0)

        # Load into target
        with target_conn.cursor() as tgt_cursor:
            tgt_cursor.execute('TRUNCATE "Attachments";')
            tgt_cursor.copy_expert(
                """
                COPY "Attachments" (id, "meetingId", "customerId","files","userId")
                FROM STDIN WITH CSV
                """,
                buffer
            )
            target_conn.commit()

        source_conn.close()
        target_conn.close()


    transfer()

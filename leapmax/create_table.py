"""
PROGRAMMER : JASKIRAT
INFO : LEAPMAX TABLE REPLICATION FROM SOURCE (LEAP PRODUCTION DB) TO TARGET (LEAPMAX DB) USING AIRFLOW
"""

# ==================== IMPORT REQUIRED LIBRARIES ====================
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

import logging
import pendulum

from leapmax.config.leapmax_config import ENABLED_TABLES, TABLES_CONFIG

# ============== LOGGER CONFIGURATION ==============
logger = logging.getLogger(__name__)

# ============== CONNECTION CONFIGURATION ==============
SOURCE_CONNECTION = "prod_ksoft_leap"
SOURCE_DB = "clxyi19290000s7kvd0rrf2ho"

DESTINATION_CONNECTION = "DI-POSTGRES"
DESTINATION_DB = "leapmax"

# ============== HELPER FUNCTIONS ==============

def get_schema(source_hook: PostgresHook, table_name: str):

    query = """
    SELECT 
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_name = %s
    AND table_schema = 'public'
    ORDER BY ordinal_position;
    """

    try:
        source_conn = source_hook.get_conn()
        source_cursor = source_conn.cursor()
        source_cursor.execute(query, (table_name,))
        columns = source_cursor.fetchall()

    except Exception as e:
        logger.error(f"J===== ERROR FETCHING COLUMNS FOR {table_name} : {e} =====S")
        raise

    finally:
        source_cursor.close()
        source_conn.close()

    return columns

def map_columns(columns: list):
    mapped_columns = {}
    datatype_mapping = {
        "integer": "INT",
        "bigint": "BIGINT",
        "numeric": "NUMERIC",
        "text": "TEXT",
        "character varying": "TEXT",
        "timestamp without time zone": "TIMESTAMP",
        "timestamp with time zone": "TIMESTAMPTZ",
        "date": "DATE",
        "boolean": "BOOLEAN",
        "json": "JSON",
        "jsonb": "JSONB",
        "double precision": "DOUBLE PRECISION",
        "uuid": "UUID",
        "array": "TEXT"
    }
    for col, datatype in columns:
        mapped_columns[col] = datatype_mapping.get(datatype, "TEXT")

    return mapped_columns


def create_table_query(destination_hook: PostgresHook, table_name: str, table_config: dict, columns: dict, is_staging:bool=False):

    primary_keys = table_config["primary_key"]

    sql_cols = [f'"{col}" {dtype}' for col, dtype in columns.items()]

    sql_cols.append('"tenant_name" TEXT')

    pk_cols = primary_keys + ["tenant_name"]
    pk_sql = f"PRIMARY KEY ({', '.join([f'"{col}"' for col in pk_cols])})"

    query = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {', '.join(sql_cols)},
            {pk_sql}
        );
    """

    if is_staging:
        query = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {', '.join(sql_cols)}
        );
        """

    try:
        destination_conn = destination_hook.get_conn()
        destination_cursor = destination_conn.cursor()
        destination_cursor.execute(query)
        destination_conn.commit()

    except Exception as e:
        logger.error(f"J===== ERROR CREATING TABLE {table_name} : {e} =====S")
        raise

    finally:
        destination_cursor.close()
        destination_conn.close()

# ============== DAG DEFINITION ==============

default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id="leapmax_raw_table_creation",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["leapmax", "raw"],
    default_args=default_args
)
def leapmax_raw_table_creation():

    # ============== PROCESSING TABLES ==============

    @task
    def create_tracking_table():
        
        query = """
        CREATE TABLE IF NOT EXISTS "leap_tracking" (
            "table_name" TEXT,
            "tenant_name" TEXT,
            "last_run" TIMESTAMP,
            "last_row_id" TEXT,
            PRIMARY KEY ("table_name", "tenant_name")
        );
        """

        try:
            destination_hook = PostgresHook(
                postgres_conn_id=DESTINATION_CONNECTION,
                database=DESTINATION_DB
            )
            destination_conn = destination_hook.get_conn()
            destination_cursor = destination_conn.cursor()
            destination_cursor.execute(query)

        except Exception as e:
            logger.error(f"J===== ERROR CREATING TABLE leap_tracking : {e} =====S")
            raise

        else:
            destination_conn.commit()
            logger.info("J===== TABLE leap_tracking CREATED SUCCESSFULLY =====S")

        finally:
            destination_cursor.close()
            destination_conn.close()

    @task
    def create_table_task(table: str):

        table_name = table
        table_config = TABLES_CONFIG[table_name]
        logger.info(f"J===== PROCESSING [{table_name}] =====S")

        # ============== CONNECTIONS ==============
        source_hook = PostgresHook(
            postgres_conn_id=SOURCE_CONNECTION,
            database=SOURCE_DB
        )
        destination_hook = PostgresHook(
            postgres_conn_id=DESTINATION_CONNECTION,
            database=DESTINATION_DB
        )

        # ============== GET SCHEMA ==============
        columns = get_schema(source_hook, table_name)
        logger.info(f"J===== COLUMNS FOR [{table_name}] : [{columns}] =====S")
        columns_mapped = map_columns(columns)
        logger.info(f"J===== MAPPED COLUMNS FOR [{table_name}] : [{columns_mapped}] =====S")

        # ============== CREATE TABLE ==============
        create_table_query(destination_hook, table_name, table_config, columns_mapped)
        logger.info(f"J===== TABLE [{table_name}] CREATED SUCCESSFULLY =====S")

        # ============== CREATE STAGING TABLE ==============
        if table_config["strategy"] == "upsert":
            staging_table = f"{table_name}_staging"
            create_table_query(destination_hook, staging_table, table_config, columns_mapped, is_staging=True)
            logger.info(f"J===== TABLE [{staging_table}] CREATED SUCCESSFULLY (STAGING) =====S")

    # ============== TASKS ==============
    tracking = create_tracking_table()
    tables = create_table_task.expand(table=ENABLED_TABLES)

    tracking >> tables

leapmax_raw_table_creation()
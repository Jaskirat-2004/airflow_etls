
"""
PROGRAMMER : JASKIRAT
INFO : LMS DAG FOR RAW TABLE CREATION
"""

from airflow.decorators import dag, task
import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

import logging
import time

from lms.config.config import TABLE_CONFIG, ENABLED_TABLES

# ================== LOGGER ==================

logger = logging.getLogger(__name__)

# ================== CONNECTIONS ==================

CLICKHOUSE_CONN_ID = "Clickhouse_Knowmax"
REFERENCE_TENANT = "wonderchefphygital"

DATABASE_NAME = "lms"
POSTGRES_CONN_ID = "DI-POSTGRES"

# ================== HELPERS FUNCTIONS ==================

def clickhouse_to_postgres(datatype: str):

    if datatype.startswith("Nullable("):
        datatype = datatype[len("Nullable("):-1]

    if datatype.startswith("LowCardinality("):
        datatype = datatype[len("LowCardinality("):-1]

    base_type = datatype.split("(")[0]

    MAPPER = {
        "Int8": "SMALLINT", "Int16": "SMALLINT",
        "Int32": "INTEGER", "Int64": "BIGINT",
        "UInt8": "SMALLINT", "UInt16": "INTEGER",
        "UInt32": "BIGINT", "UInt64": "NUMERIC(20,0)",

        "Float32": "REAL", "Float64": "DOUBLE PRECISION",

        "String": "TEXT", "FixedString": "TEXT",

        "Date": "DATE", "DateTime": "TIMESTAMP", "DateTime64": "TIMESTAMP",

        "Bool": "SMALLINT",
        "UUID": "UUID",
        "Decimal": "NUMERIC",
        "Enum8": "TEXT", "Enum16": "TEXT",
    }

    if base_type not in MAPPER:
        logger.warning(f"J====== UNKNOWN DATATYPE {datatype}, DEFAULTING TO TEXT ======S")

    return MAPPER.get(base_type, "TEXT")

def create_table_query(table_name: str, structure: list, primary_key: list):

    sql_cols = ",\n".join(structure)

    if primary_key:
        pk_cols = ['"tenant_name"'] + [f'"{col}"' for col in primary_key]
        pk_sql = f",\n    PRIMARY KEY ({', '.join(pk_cols)})"
    else:
        pk_sql = ""

    query = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
        {sql_cols}
        {pk_sql}
    );
    """

    return query

# ===============================================================================
# DAG
# ===============================================================================
default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id="lms_create_raw_tables",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["lms", "setup", "ddl"],
    default_args=default_args,
)
def create_tables_pipeline():

     # CREATING THE TRACKING TABLE
    @task
    def create_tracking_table():
        try:
            # POSTGRES CONNECTION
            pg_hook = PostgresHook(
                postgres_conn_id=POSTGRES_CONN_ID,
                database=DATABASE_NAME
            )
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()
            logger.info("J====== POSTGRES CONNECTION ESTABLISHED ======S")

            # TRACKING TABLE 
            query = f"""
                CREATE TABLE IF NOT EXISTS "lms_tracking" (
                    "table_name" TEXT NOT NULL,
                    "tenant_name" TEXT NOT NULL,
                    "last_run" TIMESTAMP NOT NULL,
                    PRIMARY KEY (table_name, tenant_name)
                )
            """

            pg_cursor.execute(query)
            pg_conn.commit()
            logger.info("J====== TRACKING TABLE CREATED ======S")

        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise
            
        finally:
            try:
                pg_cursor.close()
                pg_conn.close()
            except Exception as e:
                logger.warning(f"J====== ERROR CLOSING CONNECTION: {e} ======S")

    @task
    def create_each_tables():

        start_time = time.time()

        try:
            # CLICKHOUSE CONNECTION
            ch_conn = BaseHook.get_connection(CLICKHOUSE_CONN_ID)
            client = Client(
                host=ch_conn.host,
                user=ch_conn.login,
                password=ch_conn.password
            )
            logger.info("J====== CLICKHOUSE CONNECTION ESTABLISHED ======S")

            # POSTGRES CONNECTION
            pg_hook = PostgresHook(
                postgres_conn_id=POSTGRES_CONN_ID,
                database=DATABASE_NAME
            )
            pg_conn = pg_hook.get_conn()
            pg_cursor = pg_conn.cursor()
            logger.info("J====== POSTGRES CONNECTION ESTABLISHED ======S")

        except Exception as e:
            logger.error(f"J====== ERROR CONNECTING TO DATABASES: {e} ======S")
            raise

        t_count = 0

        try:
            for table_name in ENABLED_TABLES:

                logger.info(f"J====== PROCESSING TABLE: [{table_name}] ======S")

                config = TABLE_CONFIG[table_name]
                column_list = config["columns"]
                primary_key = config["primary_key"]

                ch_columns_list = client.execute(
                    """
                    SELECT name, type
                    FROM system.columns
                    WHERE database = %(db)s
                    AND table = %(table)s
                    ORDER BY position
                    """,
                    {
                        "db": REFERENCE_TENANT,
                        "table": table_name
                    }
                )

                if not ch_columns_list:
                    logger.warning(f"J====== [{table_name}] NOT FOUND IN [{REFERENCE_TENANT}], SKIPPING ======S")
                    continue

                ch_columns_dict = {col_name: datatype for col_name, datatype in ch_columns_list}

                table_structure = []

                for col in column_list:
                    ch_datatype = ch_columns_dict.get(col)

                    if ch_datatype:
                        pg_datatype = clickhouse_to_postgres(ch_datatype)
                    else:
                        pg_datatype = "TEXT"
                        logger.warning(f"J====== [{table_name}]: COLUMN [{col}] NOT FOUND, DEFAULTING TO TEXT ======S")

                    table_structure.append(f'"{col}" {pg_datatype}')

                table_structure.append('"tenant_name" TEXT NOT NULL')

                query = create_table_query(table_name, table_structure, primary_key)

                try:
                    pg_cursor.execute(query)
                    pg_conn.commit()
                    t_count += 1

                    logger.info(
                        f"J====== [{table_name}]: CREATED SUCCESSFULLY | COLS={len(column_list)} | PK={primary_key} ======S"
                    )

                except Exception as e:
                    logger.error(f"J====== ERROR CREATING TABLE [{table_name}]: {e} ======S")
                    pg_conn.rollback()
                    raise

        finally:
            try:
                pg_conn.close()
            except Exception as e:
                logger.warning(f"J====== ERROR CLOSING CONNECTION: {e} ======S")

        logger.info(
            f"J====== TABLE CREATION COMPLETED | CREATED {t_count}/{len(ENABLED_TABLES)} TABLES "
            f"IN {round(time.time() - start_time, 2)} SEC ======S"
        )
    
    # =============== CALLING THE TASKS ===============
    create_tracking_table()
    create_each_tables()

create_tables_pipeline()
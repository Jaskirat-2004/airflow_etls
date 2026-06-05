"""
PROGRAMMER : JASKIRAT
INFO : MAXICUS ETL FOR DATA MIGRATION 
"""

# ==================== IMPORT REQUIRED LIBRARIES ====================
from airflow.decorators import dag,task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.task_group import TaskGroup

import logging
import pendulum
import io

from lms.config.maxicus_config import (
    ENABLED_TABLES,
    TABLES_CONFIG,
    TENANT_DB_MAP,
    TENANTS
)

# ============== LOGGER CONFIGURATION ==============
logger =logging.getLogger(__name__)

# ============== CONNECTION CONFIGURATION ==============
SOURCE_CONNECTION = "prod_ksoft_leap"
source_db = "" # will be populated from config

DESTINATION_CONNECTION = "DI-POSTGRES"
DESTINATION_DB = "maxicus"

BATCH_SIZE = 100000
# ============== HELPER FUNCTIONS ==============

def get_last(dest_cursor, table:str, tenant:str):

    query = f"""
    SELECT "last_run","last_row_id"
    FROM "leap_tracking"
    WHERE "table_name" = %s AND "tenant_name" = %s
    LIMIT 1
    """

    try:
        dest_cursor.execute(query, (table, tenant))
        result = dest_cursor.fetchone()

        if result:
            last_run = result[0] if result and result[0] is not None else pendulum.datetime(1970,1,1, tz="UTC")
            last_row_id = int(result[1]) if result and result[1] is not None else 0

        else:
            last_run = pendulum.datetime(1970,1,1)
            last_row_id = 0

            logger.info(f"J===== NO LAST RUN FOUND FOR [{table}] | [{tenant}] (TAKING DEFAULT VALUES (1970-01-01 | 0))=====S")

        
    except Exception as e:
        logger.error(f"J===== ERROR FETCHING LAST RUN FOR [{table}] | [{tenant}] | ERROR : {e} =====S")
        raise

    else:
        logger.info(f"J===== LAST RUN FOR [{table}] | [{tenant}] : [{last_run}] | [{last_row_id}] =====S")

    last_run = last_run.strftime("%Y-%m-%d %H:%M:%S")
    return last_run,last_row_id
    
def update_last(dest_cursor, table:str, tenant:str, last_run, last_row_id:int):

    query = f"""
    INSERT INTO leap_tracking (table_name,tenant_name,last_run,last_row_id)
    VALUES (%s,%s,%s,%s)
    ON CONFLICT (table_name, tenant_name) 
    DO UPDATE SET
        last_run = EXCLUDED.last_run,
        last_row_id = EXCLUDED.last_row_id
    """

    try:
        dest_cursor.execute(query, (table, tenant, last_run, last_row_id))

    except Exception as e:
        logger.error(f"J===== ERROR UPDATING LAST RUN FOR [{table}] | [{tenant}] | ERROR : {e} =====S")
        raise

    else:
        logger.info(f"J===== LAST RUN FOR [{table}] | [{tenant}] UPDATED SUCCESSFULLY TO [{last_run}] | [{last_row_id}] =====S")

def get_last_from_dest(dest_cursor, table: str, tenant: str, table_config: dict):

    primary_key = table_config["primary_key"][0]
    incremental_column = table_config["incremental_column"]

    query = f"""
        SELECT 
            COALESCE(MAX("{primary_key}"), 0),
            MAX("{incremental_column}")
        FROM "{table}"
        WHERE tenant_name = %s
    """

    try:
        dest_cursor.execute(query, (tenant,))
        result = dest_cursor.fetchone()

        last_row_id = int(result[0]) if result and result[0] is not None else 0
        last_run = result[1] if result and result[1] is not None else pendulum.datetime(1970,1,1, tz="UTC")
        last_run = last_run.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        logger.error(f"J===== ERROR FETCHING LAST FROM DEST | [{table}] | [{tenant}] | ERROR: {e} =====S")
        raise

    else:
        logger.info(f"J===== DESTINATION LAST STATE [{table}] | [{tenant}] : [{last_run}] | [{last_row_id}] =====S")

    return last_run, last_row_id
    
def copy_batch(source_cursor, dest_cursor, select_query:str, table:str):

    buffer = io.StringIO()

    copy_out_query = f"""
        COPY ({select_query}) TO STDOUT WITH CSV
        """

    copy_in_query = f"""
        COPY "{table}" FROM STDIN WITH CSV
        """

    # ==================== EXTRACT ====================
    logger.info(f"J===== EXTRACTING DATA START =====S")

    source_cursor.copy_expert(
        copy_out_query,
        buffer
    )

    logger.info(f"J===== EXTRACTING DATA DONE =====S")

    if buffer.tell() == 0:
        return False

    buffer.seek(0)

    # ==================== LOAD ====================
    logger.info(f"J===== LOADING DATA =====S")
    dest_cursor.copy_expert(
        copy_in_query,
        buffer
    )

    return True 

def handle_append(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    incremental_column = table_config["incremental_column"]
    primary_key = table_config["primary_key"][0] # We need only id column as primary key (sequencial)

    # ==================== FETCH LAST RUN ====================
    last_run,last_row_id = get_last(dest_cursor, table, tenant)

    rows_processed = 0
    batch_count = 0

    # COLUMNS
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]

    column_list = ', '.join([f'"{col}"' for col in columns])

    while True :

        # ==================== FETCH DATA FROM SOURCE ====================
        
        select_query = f"""
            SELECT {column_list}, '{tenant}' AS tenant_name
            FROM "{table}"
            WHERE "{incremental_column}" > '{last_run}'
            ORDER BY "{incremental_column}"
            LIMIT {BATCH_SIZE}
        """
        # ==================== COPY BATCH ====================
        has_data = copy_batch(
            source_cursor,
            dest_cursor,
            select_query,
            table,
        )

        dest_cursor.commit()

        if not has_data:
            logger.info(f"J===== NO NEW DATA FOUND FOR [{table}] | [{tenant}] =====S")
            break
        
        # ==================== UPDATE LAST RUN ====================
        new_last_run, new_last_row_id = get_last_from_dest(
            dest_cursor,
            table,
            tenant,
            table_config
        )

        rows_processed += new_last_row_id - last_row_id
        batch_count += 1

        logger.info(f"J===== [{table}] | [{tenant}] | BATCH : [{batch_count}] | TOTAL ROWS PROCESSED : [{rows_processed}] =====S")
        
        last_run = new_last_run
        last_row_id = new_last_row_id

        logger.info(f"J===== [{table}] | [{tenant}] | TILL NOW LAST RUN : [{last_run}] | TILL NOW LAST ROW ID : [{last_row_id}] =====S")

        # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
        update_last(dest_cursor, table, tenant, last_run, last_row_id)
        logger.info(f"J===== [{table}] | [{tenant}] | APPEND COMPLETED SUCCESSFULLY =====S")

def handle_upsert(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    # ==================== STAGING TABLE ====================
    staging_table = f"{table}_staging"
    
    incremental_column = table_config["incremental_column"]
    primary_key = table_config["primary_key"][0]

    # ==================== FETCH LAST RUN ====================
    last_run,last_row_id = get_last(dest_cursor, table, tenant)

    rows_processed = 0
    batch_count = 0

    # ==================== GET COLUMN LIST ====================
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]

    column_list = ', '.join([f'"{col}"' for col in columns])

    # ==================== PREPARE MERGE QUERY ====================
    update_cols = [
        col for col in columns 
        if col != primary_key
    ]
    insert_cols = columns + ["tenant_name"]
    conflict_cols = [primary_key] + ["tenant_name"]

    insert_cols_sql = ", ".join([f'"{col}"' for col in insert_cols])
    select_cols_sql = ", ".join([f'"{col}"' for col in insert_cols])
    conflict_cols_sql = ", ".join([f'"{col}"' for col in conflict_cols])
    
    update_set_sql = ", ".join([
        f'"{col}" = EXCLUDED."{col}"'
        for col in update_cols
    ])

    update_where_sql = ' OR '.join([
        f'"{table}"."{col}" IS DISTINCT FROM EXCLUDED."{col}"'
        for col in update_cols
    ])
    # ==================== MERGE DATA ====================
    merge_query = f"""
    INSERT INTO "{table}" ({insert_cols_sql})
    SELECT {select_cols_sql}
    FROM "{staging_table}"
    ON CONFLICT ({conflict_cols_sql})
    DO UPDATE SET
        {update_set_sql}
    WHERE 
        {update_where_sql};
    """

    while True:

        # ==================== FETCH DATA ====================
        select_query = f"""
            SELECT {column_list}, '{tenant}' AS tenant_name
            FROM "{table}"
            WHERE "{incremental_column}" > '{last_run}'
            ORDER BY "{incremental_column}"
            LIMIT {BATCH_SIZE}
        """

        has_data = copy_batch(
            source_cursor,
            dest_cursor,
            select_query,
            staging_table, # DATA COPIED TO STAGING TABLE 
        )

        if not has_data:
            logger.info(f"J===== NO NEW DATA FOUND FOR [{table}] | [{tenant}] =====S")
            break

        # ==================== DEDUP ====================
        dedup_query = f"""
        DELETE FROM "{staging_table}"
        WHERE ctid NOT IN (
            SELECT ctid FROM(
                SELECT ctid,
                    ROW_NUMBER() OVER (
                        PARTITION BY "{primary_key}", tenant_name
                        ORDER BY "{incremental_column}" DESC, "{primary_key}" DESC
                    ) as rn
                FROM "{staging_table}"
            ) t
            WHERE t.rn = 1
        )
        """

        try:
            dest_cursor.execute(dedup_query)
            logger.info(f"J===== DEDUP COMPLETED FOR [{staging_table}] | [{tenant}] =====S")
        except Exception as e:
            logger.error(f"J===== ERROR IN DEDUP FOR [{staging_table}] | [{tenant}] | ERROR : {e} =====S")
            raise
        
        # ==================== MERGE ====================
        try:
            dest_cursor.execute(merge_query)
            rows_affected = dest_cursor.rowcount
            logger.info(f"J===== MERGE AFFECTED {rows_affected} ROWS FOR [{table}] | [{tenant}] =====S")
        except Exception as e:
            logger.error(f"J===== ERROR IN MERGE FOR [{table}] | [{tenant}] | ERROR : {e} =====S")
            raise

        # ==================== TRUNCATE STAGING TABLE ====================
        truncate_query = f'TRUNCATE TABLE "{staging_table}"'

        try:
            dest_cursor.execute(truncate_query)
            logger.info(f"J===== TRUNCATE COMPLETED FOR [{staging_table}] | [{tenant}] =====S")
        except Exception as e:
            logger.error(f"J===== ERROR IN TRUNCATE FOR [{staging_table}] | [{tenant}] | ERROR : {e} =====S")
            raise

        # ==================== UPDATE LAST RUN ====================
        new_last_run, new_last_row_id = get_last_from_dest(
            dest_cursor,
            table,
            tenant,
            table_config
        )

        rows_processed += new_last_row_id - last_row_id
        batch_count += 1
        
        logger.info(f"J===== [{staging_table}] | [{tenant}] | BATCH : [{batch_count}] | TOTAL ROWS PROCESSED : [{rows_processed}] =====S")
        
        last_run = new_last_run
        last_row_id = new_last_row_id

        logger.info(f"J===== [{table}] | [{tenant}] | TILL NOW LAST RUN : [{last_run}] | TILL NOW LAST ROW ID : [{last_row_id}] =====S")


        # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
        update_last(dest_cursor, table, tenant, last_run, last_row_id)
        logger.info(f"J===== [{table}] | [{tenant}] | MERGE COMPLETED SUCCESSFULLY =====S")


def handle_full_refresh(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    # ==================== GET COLUMN LIST ====================
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]
    column_list = ', '.join([f'"{col}"' for col in columns])

    # ==================== COPY ALL DATA ====================
    select_query = f"""
    SELECT {column_list}, '{tenant}' AS tenant_name
    FROM "{table}"
    """

    has_data  = copy_batch(
        source_cursor,
        dest_cursor,
        select_query,
        table,
    )
    
    if not has_data:
        logger.info(f"J===== NO DATA FOUND FOR [{table}] | [{tenant}] =====S")
        return

    # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
    update_last(dest_cursor, table, tenant, pendulum.now(), 0)
    logger.info(f"J===== FULL REFRESH DONE: [{table}] | [{tenant}] =====S")


# ============== DAG DEFINITION ==============
default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id = "maxicus_etl",
    start_date = pendulum.datetime(2026,1,1),
    schedule = None,
    catchup = False,
    max_active_runs = 5,
    tags = ["maxicus"],
    default_args = default_args
)
def maxicus_etl():
    
    logger.info("J===== STARTING MAXICUS ETL =====S")

    @task
    def truncate_full_refresh_tables(table:str):

        table_config = TABLES_CONFIG[table]
        strategy = table_config["strategy"]

        if strategy != "full_refresh":
            return
        else:
            query = f"""
            TRUNCATE TABLE "{table}"
            """
            
            dest_hook = PostgresHook(
                postgres_conn_id = DESTINATION_CONNECTION,
                database = DESTINATION_DB
            )
            dest_conn = dest_hook.get_conn()
            dest_cursor = dest_conn.cursor()

            dest_cursor.execute(query)
            dest_conn.commit()
            logger.info(f"J===== TRUNCATE COMPLETED FOR [{table}] =====S")
        
    # ============== PROCESSING TABLES ==============

    @task
    def migrate_tables(table: str, tenant: str):
        
        table_config = TABLES_CONFIG[table]
        strategy = table_config["strategy"]
        
        SOURCE_DB = TENANT_DB_MAP[tenant]

        logger.info(f"J===== TABLE: [{table}] | TENANT: [{tenant}] | STRATEGY: [{strategy}] =====S")
        
        # ============== DATABASE CONNECTIONS ==============
        try:
            dest_hook = PostgresHook(
                    postgres_conn_id = DESTINATION_CONNECTION,
                    database = DESTINATION_DB
                )
            dest_conn = dest_hook.get_conn()
            dest_cursor = dest_conn.cursor()

            source_hook = PostgresHook(
                postgres_conn_id = SOURCE_CONNECTION,
                database = SOURCE_DB
                )
            source_conn = source_hook.get_conn()
            source_cursor = source_conn.cursor()

        except Exception as e:
            logger.error(f"J===== ERROR CONNECTING TO DATABASES FOR [{table}] : {e} =====S")
            raise

        else:
            logger.info(f"J===== DATABASES CONNECTED SUCCESSFULLY FOR [{table}] | [{tenant}] =====S")

            # ============================ STRATEGY HANDLING ============================
            try:
                if strategy == "append":
                    handle_append(source_cursor, dest_cursor, table, tenant, table_config)

                elif strategy == "upsert":
                    handle_upsert(source_cursor, dest_cursor, table, tenant, table_config)

                elif strategy == "full_refresh":
                    handle_full_refresh(source_cursor, dest_cursor, table, tenant, table_config)

                else:
                    logger.error(f"J===== UNKNOWN STRATEGY: [{strategy}] =====S")
                    raise ValueError(f"Unknown strategy: [{strategy}]")
            
            except Exception as e:
                dest_conn.rollback()
                logger.exception(f"ERROR IN [{table}] | [{tenant}]")
                raise

            else:
                dest_conn.commit()

        finally:
            if 'source_cursor' in locals():
                source_cursor.close()
            if 'source_conn' in locals():
                source_conn.close()
            if 'dest_cursor' in locals():
                dest_cursor.close()
            if 'dest_conn' in locals():
                dest_conn.close()

    # =========================
    # STRATING TASKS
    # =========================

    for table in ENABLED_TABLES:

        table_config = TABLES_CONFIG[table]
        strategy = table_config["strategy"]

        with TaskGroup(group_id=f"{table}"):

            # TRUNCATE
            truncate_task = None

            if strategy == "full_refresh":
                truncate_task = truncate_full_refresh_tables.override(
                task_id=f"truncate_{table}"
            )(table=table)

            # TENANT TASKS
            previous_task = None
            first_task = None

            for tenant in TENANTS:

                current_task = migrate_tables.override(
                    task_id=f"{table}_{tenant}"
                )(table=table, tenant=tenant)

                # capture first task
                if first_task is None:
                    first_task = current_task

                # chain tenants
                if previous_task:
                    previous_task >> current_task

                previous_task = current_task

            # CONNECT TRUNCATE → FIRST TASK
            if truncate_task:
                truncate_task >> first_task

maxicus_etl()
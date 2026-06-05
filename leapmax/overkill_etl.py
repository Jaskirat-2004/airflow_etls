"""
PROGRAMMER : JASKIRAT
INFO : LEAPMAX ETL FOR DATA MIGRATION (APPEND, UPSERT, FULL REFRESH, TIME SERIES)
"""

# ==================== IMPORT REQUIRED LIBRARIES ====================
from airflow.decorators import dag,task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.task_group import TaskGroup

import logging
import pendulum
import io

from leapmax.config.leapmax_overkill_config import (
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
DESTINATION_DB = "leapmax"

BATCH_SIZE = 100000

# FOR MANUAL RUNS 
START_DATE = pendulum.datetime(2026,2,2, tz="UTC")
END_DATE = pendulum.datetime(2026,4,13, tz="UTC")

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
            last_run = result[0] if result and result[0] is not None else START_DATE
            last_row_id = int(result[1]) if result and result[1] is not None else 0

        else:
            last_run = START_DATE
            last_row_id = 0

            logger.info(f"J===== NO LAST RUN FOUND FOR [{table}] | [{tenant}] (TAKING DEFAULT VALUES ({START_DATE} | 0))=====S")

        
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
    
def copy_batch(source_cursor, dest_cursor, select_query:str, table:str):

    buffer = io.StringIO()

    copy_out_query = f"""
        COPY ({select_query}) TO STDOUT WITH CSV
        """

    copy_in_query = f"""
        COPY "{table}" FROM STDIN WITH CSV
        """

    try:
        # ==================== EXTRACT ====================
        logger.info(f"J===== EXTRACTING DATA START =====S")
        source_cursor.copy_expert(
            copy_out_query,
            buffer
        )
        logger.info(f"J===== EXTRACTING DATA DONE | SIZE: {buffer.tell()} bytes =====S")

        if buffer.tell() == 0:
            return False
        
        buffer.seek(0)
        # ==================== LOAD ====================
        logger.info(f"J===== LOADING DATA =====S")
        dest_cursor.copy_expert(
            copy_in_query,
            buffer
        )
    except Exception as e:
        logger.error(f"J===== ERROR COPYING BATCH FOR [{table}] | ERROR: {e} =====S")
        raise
    else:
        dest_cursor.connection.commit()
        logger.info(f"J===== BATCH COMMITTED SUCCESSFULLY =====S")

    return True 

def handle_append(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    incremental_column = table_config["incremental_column"]
    primary_key = table_config["primary_key"][0]

    # ==================== FETCH LAST RUN ====================
    last_run,last_row_id = get_last(dest_cursor, table, tenant)

    batch_count = 0
    window_start = pendulum.parse(last_run)
    final_end = pendulum.now()
    window_interval = 300 # IN MINUTES

    # ==================== GET COLUMN LIST ====================
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]

    column_list = ', '.join([f'"{col}"' for col in columns])

    while window_start < final_end :

        window_end = window_start + pendulum.duration(minutes=window_interval)

        # ==================== FETCH DATA FROM SOURCE ====================
        
        select_query = f"""
            SELECT {column_list}, '{tenant}' AS tenant_name
            FROM "{table}"
            WHERE "{incremental_column}" >= '{window_start}'
            AND "{incremental_column}" < '{window_end}'
            ORDER BY "{incremental_column}"
        """
        # ==================== COPY BATCH ====================
        logger.info(f"J===== PROCESSING WINDOW [{window_start} → {window_end}] =====S")

        has_data = copy_batch(
            source_cursor,
            dest_cursor,
            select_query,
            table,
        )

        if not has_data:
            logger.info(f"J===== NO DATA FOUND FOR [{table}] | [{tenant}] | WINDOW : [{window_start} - {window_end}] =====S")
        
        # ==================== UPDATE WINDOW ====================
        window_start = window_end
        batch_count += 1

        logger.info(f"J===== [{table}] | [{tenant}] | BATCH : [{batch_count}] =====S")
        
        update_last(dest_cursor, table, tenant, window_start, last_row_id)
    # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
    id_query = f"""
    SELECT MAX("{primary_key}") 
    FROM "{table}" 
    WHERE tenant_name = '{tenant}'
    """
    dest_cursor.execute(id_query)
    max_id = dest_cursor.fetchone()[0]
    update_last(dest_cursor, table, tenant, window_start, max_id)
    logger.info(f"J===== TRACKING TABLE UPDATED FOR [{table}] | [{tenant}] | FINAL LAST RUN : [{window_start}] | LAST ROW ID : [{max_id}] =====S")
    logger.info(f"J===== APPEND COMPLETED SUCCESSFULLY FOR [{table}] | [{tenant}] =====S")

def handle_upsert(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    # ==================== STAGING TABLE ====================
    staging_table = f"{table}_staging"
    
    incremental_column = table_config["incremental_column"]
    primary_key = table_config["primary_key"][0]

    # ==================== FETCH LAST RUN ====================
    last_run,total_rows = get_last(dest_cursor, table, tenant)

    batch_count = 0

    # ==================== GET COLUMN LIST ====================
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]

    column_list = ', '.join([f'"{col}"' for col in columns])

    # ==================== PREPARE MERGE QUERY ====================
    update_cols = [
        col for col in columns 
        if col not in primary_key
    ]

    insert_cols = columns + ["tenant_name"]
    conflict_cols = [primary_key] + ["tenant_name"]

    insert_cols_sql = ", ".join([f'"{col}"' for col in insert_cols])
    conflict_cols_sql = ", ".join([f'"{col}"' for col in conflict_cols])
    
    update_set_sql = ", ".join([
        f'"{col}" = EXCLUDED."{col}"'
        for col in update_cols
    ])

    dest_cursor.execute(f'TRUNCATE TABLE "{staging_table}"')

    # ==================== FETCH DATA ====================
    select_query = f"""
        SELECT {column_list}, '{tenant}' AS tenant_name
        FROM "{table}"
        WHERE "{incremental_column}" > '{last_run}'
        ORDER BY "{incremental_column}"
    """

    has_data = copy_batch(
        source_cursor,
        dest_cursor,
        select_query,
        staging_table, # DATA COPIED TO STAGING TABLE 
    )

    if not has_data:
        logger.info(f"J===== NO DATA FOUND FOR [{table}] | [{tenant}] =====S")
        return
    
    # ==================== MERGE ====================
    merge_query = f"""
        INSERT INTO "{table}" ({insert_cols_sql})
        SELECT {insert_cols_sql}
        FROM "{staging_table}"
        ON CONFLICT ({conflict_cols_sql})
        DO UPDATE SET
            {update_set_sql}
    """
    try:
        dest_cursor.execute(merge_query)
        rows_affected = dest_cursor.rowcount
        logger.info(f"J===== MERGE AFFECTED {rows_affected} ROWS FOR [{table}] | [{tenant}] =====S")
    except Exception as e:
        logger.error(f"J===== ERROR IN MERGE FOR [{table}] | [{tenant}] | ERROR : {e} =====S")
        raise
    
    # ==================== UPDATE LAST RUN ====================
    dest_cursor.execute(f"""
        SELECT MAX("{incremental_column}")
        FROM "{staging_table}"
    """)
    new_last_run = dest_cursor.fetchone()[0]
    
    last_run = new_last_run

    # ==================== TRUNCATE STAGING TABLE ====================
    truncate_query = f'TRUNCATE TABLE "{staging_table}"'
    try:
        dest_cursor.execute(truncate_query)
        logger.info(f"J===== TRUNCATE COMPLETED FOR [{staging_table}] | [{tenant}] =====S")
    except Exception as e:
        logger.error(f"J===== ERROR IN TRUNCATE FOR [{staging_table}] | [{tenant}] | ERROR : {e} =====S")
        raise

    batch_count += 1
    
    logger.info(f"J===== [{staging_table}] | [{tenant}] | BATCH : [{batch_count}] =====S")

    # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
    id_query = f"""
    SELECT MAX("{primary_key}") 
    FROM "{table}" 
    WHERE tenant_name = '{tenant}'
    """
    dest_cursor.execute(id_query)
    max_id = dest_cursor.fetchone()[0]
    update_last(dest_cursor, table, tenant, last_run, max_id)
    logger.info(f"J===== TRACKING TABLE UPDATED FOR [{table}] | [{tenant}] | FINAL LAST RUN : [{last_run}] | MAX ID : [{max_id}] =====S")
    logger.info(f"J===== UPSERT COMPLETED SUCCESSFULLY FOR [{table}] | [{tenant}] =====S")

def handle_full_refresh(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    primary_key = table_config["primary_key"][0]

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
    id_query = f"""
    SELECT MAX("{primary_key}")
    FROM "{table}"
    WHERE tenant_name = '{tenant}'
    """
    dest_cursor.execute(id_query)
    max_id = dest_cursor.fetchone()[0]

    update_last(dest_cursor, table, tenant, pendulum.now(), max_id)
    logger.info(f"J===== FULL REFRESH DONE: [{table}] | [{tenant}] | MAX ID : [{max_id}] =====S")

def handle_time_series(source_cursor, dest_cursor, table:str, tenant:str, table_config:dict):

    incremental_column = table_config["incremental_column"]
    primary_key = table_config["primary_key"][0]

    # ==================== FETCH LAST RUN ====================
    last_run,last_row_id = get_last(dest_cursor, table, tenant)

    batch_count = 0
    window_start = pendulum.parse(last_run) if last_run else START_DATE
    final_end = pendulum.now()
    window_interval = 30 # IN MINUTES

    # ==================== GET COLUMN LIST ====================
    source_cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
    columns = [desc[0] for desc in source_cursor.description]

    column_list = ', '.join([f'"{col}"' for col in columns])

    while window_start < final_end :

        window_end = window_start + pendulum.duration(minutes=window_interval)

        # ==================== FETCH DATA FROM SOURCE ====================
        
        select_query = f"""
            SELECT {column_list}, '{tenant}' AS tenant_name
            FROM "{table}"
            WHERE "{incremental_column}" >= '{window_start}'
            AND "{incremental_column}" < '{window_end}'
            ORDER BY "{incremental_column}"
        """
        # ==================== COPY BATCH ====================
        logger.info(f"J===== PROCESSING WINDOW [{window_start} → {window_end}] =====S")

        has_data = copy_batch(
            source_cursor,
            dest_cursor,
            select_query,
            table,
        )

        if not has_data:
            logger.info(f"J===== NO DATA FOUND FOR [{table}] | [{tenant}] | WINDOW : [{window_start} - {window_end}] =====S")
        
        # ==================== UPDATE WINDOW ====================
        window_start = window_end
        batch_count += 1

        logger.info(f"J===== [{table}] | [{tenant}] | BATCH : [{batch_count}] =====S")
        
        update_last(dest_cursor, table, tenant, window_start, last_row_id)
    # ==================== UPDATE LAST RUN IN TRACKING TABLE ====================
    id_query = f"""
    SELECT MAX("{primary_key}") 
    FROM "{table}" 
    WHERE tenant_name = '{tenant}'
    """
    dest_cursor.execute(id_query)
    last_row_id = dest_cursor.fetchone()[0]
    update_last(dest_cursor, table, tenant, window_start, last_row_id)
    logger.info(f"J===== TRACKING TABLE UPDATED FOR [{table}] | [{tenant}] | FINAL LAST RUN : [{window_start}] | LAST ROW ID : [{last_row_id}] =====S")
    logger.info(f"J===== TIME SERIES COMPLETED SUCCESSFULLY FOR [{table}] | [{tenant}] =====S")

# ============== DAG DEFINITION ==============
default_args = {
    "owner": "JASKIRAT",
}

@dag(
    dag_id = "leapmax_overkill_etl",
    start_date = pendulum.datetime(2026,1,1),
    schedule = None,
    catchup = False,
    max_active_runs = 5,
    tags = ["leapmax","overkill"],
    default_args = default_args
)
def leapmax_overkill_etl():
    
    logger.info("J===== STARTING LEAPMAX OVERKILL ETL =====S")

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

                elif strategy == "time_series":
                    handle_time_series(source_cursor, dest_cursor, table, tenant, table_config)

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

leapmax_overkill_etl()
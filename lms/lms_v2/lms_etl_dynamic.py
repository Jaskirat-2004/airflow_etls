"""
PROGRAMMER : JASKIRAT
INFO : LMS ETL FOR DATA MIGRATION 
"""

from airflow.decorators import dag, task
from airflow.utils.task_group import TaskGroup

import pendulum

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.hooks.base import BaseHook
from clickhouse_driver import Client

import logging

from lms.config.config import TABLE_CONFIG, ENABLED_TABLES, TENANTS, TENNAT_MAPPER_SAMPARK

# ===============================================================================
# LOGGER
# ===============================================================================

logger = logging.getLogger(__name__)

# ===============================================================================
# CONNECTION CONFIG
# ===============================================================================

CLICKHOUSE_CONN_ID = "Clickhouse_Knowmax"

POSTGRES_CONN_ID   = "DI-POSTGRES"
DATABASE_NAME      = "lms"

BATCH_SIZE = 5000

# ===============================================================================
# HELPER FUNCTIONS AND QUERIES
# ===============================================================================

def build_columns(columns:list,casts:dict):

    sql_cols = []

    for col in columns:
        if casts and col in casts:
            cast = casts[col]
            sql_cols.append(f"{cast}(`{col}`) AS `{col}`")
        else:
            sql_cols.append(f'`{col}`')
    
    return ", ".join(sql_cols)

def select_query(table_name:str,columns:list,tenant_name:str,casts = None):

    # FOR RLS (SAMPARK) DB names differnt then those in sampark
    tenant_name_sampark = TENNAT_MAPPER_SAMPARK.get(tenant_name,tenant_name)
    
    sql_cols = build_columns(columns,casts)
    
    query = f"""
        SELECT {sql_cols}, '{tenant_name_sampark}' as tenant_name
        FROM `{tenant_name}`.`{table_name}`
    """
    
    return query

def select_incremental_query(
    table_name:str,
    columns:list,
    tenant_name:str,
    incremental_col:str,
    last_run:str,
    casts = None
):
    
    sql_cols = build_columns(columns,casts)

    # FOR RLS (SAMPARK) DB names differnt then those in sampark
    tenant_name_sampark = TENNAT_MAPPER_SAMPARK.get(tenant_name,tenant_name)

    query = f"""
        SELECT {sql_cols}, '{tenant_name_sampark}' as tenant_name
        FROM `{tenant_name}`.`{table_name}`
        WHERE `{incremental_col}` >= '{last_run}'
        ORDER BY `{incremental_col}` ASC
        LIMIT {BATCH_SIZE}
    """

    return query

def insert_query(table_name:str,columns:list,primary_key:str):

    sql_cols = ", ".join([f'"{col}"' for col in columns] + ["tenant_name"])
    placeholders = ", ".join(["%s"] * (len(columns) + 1))

    # FOR FULL LOAD (NO PRIMARY KEY (None))
    if not primary_key:
        query = f"""
            INSERT INTO "{table_name}" (
                {sql_cols}
            )
            VALUES({placeholders})
        """
        return query
    
    # FOR INCREMENTAL LOAD (WITH PRIMARY KEY)
    if not isinstance(primary_key, list):
        primary_key = [primary_key]

    update_cols = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns])
    
    query = f"""
        INSERT INTO "{table_name}" (
            {sql_cols}
        )
        VALUES({placeholders})
        ON CONFLICT (tenant_name, {', '.join(primary_key)})
        DO UPDATE SET
            {update_cols}
    """
    
    return query

def get_last_run(pg_cursor,table_name:str,tenant_name:str):

    query = f"""
        SELECT last_run
        FROM lms_tracking
        WHERE table_name = %s AND tenant_name = %s
    """
    pg_cursor.execute(query,(table_name,tenant_name))
    result = pg_cursor.fetchone()

    return result[0] if result else None

def update_last_run(pg_cursor,table_name:str,tenant_name:str,last_run:str):

    query = f"""
        INSERT INTO "lms_tracking" (
            "table_name",
            "tenant_name",
            "last_run"
        )
        VALUES(%s,%s,%s)
        ON CONFLICT (table_name,tenant_name)
        DO UPDATE SET
            "last_run" = EXCLUDED."last_run"
    """

    pg_cursor.execute(query,(table_name,tenant_name,last_run))

# ===============================================================================
# DAG
# ===============================================================================

default_args ={
    "owner": "JASKIRAT",
}

@dag(
    dag_id="lms_etl_dynamic",
    start_date=pendulum.datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_tasks=12,
    tags=["lms", "etl", "dynamic"],
    default_args=default_args,
)
def lms_etl_pipeline():

    @task
    def process_table_tenant(table_name: str, tenant_name: str):
        
        # FOR RLS (SAMPARK) DB names differnt then those in sampark
        tenant_name_sampark = TENNAT_MAPPER_SAMPARK.get(tenant_name,tenant_name)

        logger.info(f"J====== STARTING TABLE: [{table_name}] | TENANT: [{tenant_name}] ======S")

        config = TABLE_CONFIG[table_name]
        columns = config["columns"]
        primary_key = config["primary_key"]
        incremental_column = config["incremental_column"]
        casts = config.get("casts", None)

        if casts:
            logger.info(f"J====== [{table_name}] | [{tenant_name}] → FETCHED CASTS: [{casts}] ======S")

        # ===================== CONNECTIONS =====================
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

        try:

            if incremental_column and primary_key:

                # ===================== GET LAST RUN DATE =====================
                result = get_last_run(pg_cursor,table_name,tenant_name)

                if result:
                    last_run = result
                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → LAST RUN: [{last_run}] ======S")
                else:
                    last_run = '1970-01-01'
                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → NO PREVIOUS RUN FOUND (1970-01-01 AS LAST RUN) ======S")

                # ===================== BATCHING LOOP =====================
                row_fetched = 0
                row_inserted = 0

                while True:

                    select_query_ch = select_incremental_query(
                        table_name,
                        columns,
                        tenant_name,
                        incremental_column,
                        last_run,
                        casts
                    )
                    rows = client.execute(select_query_ch)

                    if not rows:
                        logger.info(f"J====== [{table_name}] | [{tenant_name}] → NO MORE DATA FOUND ======S")
                        break

                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → FETCHED [{len(rows)}] ROWS ======S")

                    row_fetched += len(rows)

                    # ===================== INSERTING DATA INTO POSTGRES =====================
                    try:
                        insert_query_pg = insert_query(table_name,columns,primary_key)
                        pg_cursor.executemany(insert_query_pg,rows)
                        pg_conn.commit()

                        logger.info(f"J====== [{table_name}] | [{tenant_name}] → INSERTED [{len(rows)}] ROWS (INCREMENTAL LOAD) ======S")

                        row_inserted += len(rows)

                    except Exception as e:
                        logger.error(f"J====== ERROR INSERTING DATA INTO POSTGRES: {e} ======S")
                        pg_conn.rollback()
                        raise
                    
                    # ===================== UPDATE LAST RUN DATE =====================
                    last_run = rows[-1][columns.index(incremental_column)]
                    last_run = last_run.strftime("%Y-%m-%d %H:%M:%S")

                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → LAST RUN FOR THIS BATCH: [{last_run}] ======S")

                    if len(rows)<BATCH_SIZE:
                        break

                # ===================== UPDATE LAST RUN DATE IN TRACKING TABLE =====================
                update_last_run(pg_cursor,table_name,tenant_name,last_run)
                pg_conn.commit()
                logger.info(f"J====== [{table_name}] | [{tenant_name}] → LAST RUN UPDATED IN TRACKING TABLE ======S")

                logger.info(f"J====== [{table_name}] | [{tenant_name}] | TOTAL ROWS INSERTED: [{row_inserted}] | TOTAL ROWS FETCHED: [{row_fetched}] | LAST RUN: [{last_run}] | INCREMENTAL LOAD COMPLETED ======S")

            else:
                # ===================== TRUNCATE TABLE =====================
                delete_query = f'DELETE FROM "{table_name}" WHERE tenant_name = %s'
                pg_cursor.execute(delete_query, (tenant_name,))
                pg_conn.commit()
                logger.info(f"J====== [{table_name}] | [{tenant_name}] → OLD DATA DELETED ======S")

                # ===================== FETCHING DATA FROM CLICKHOUSE =====================
                try:
                    select_query_ch = select_query(table_name,columns,tenant_name,casts)
                    rows = client.execute(select_query_ch)

                    if not rows:
                        logger.info(f"J====== [{table_name}] | [{tenant_name}] → NO DATA FOUND ======S")
                        return    

                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → FETCHED [{len(rows)}] ROWS ======S")

                except Exception as e:
                    logger.error(f"J====== ERROR FETCHING DATA FROM CLICKHOUSE: {e} ======S")
                    raise
                
                # ===================== INSERTING DATA INTO POSTGRES =====================
                try:
                    insert_query_pg = insert_query(table_name,columns,primary_key)
                    pg_cursor.executemany(insert_query_pg,rows)
                    pg_conn.commit()

                    logger.info(f"J====== [{table_name}] | [{tenant_name}] → INSERTED [{len(rows)}] ROWS (FULL LOAD) ======S")
                
                except Exception as e:
                    logger.error(f"J====== ERROR INSERTING DATA INTO POSTGRES: {e} ======S")
                    pg_conn.rollback()
                    raise
            
        finally:
            try:
                pg_cursor.close()
                pg_conn.close()
            except Exception as e:
                logger.warning(f"J====== ERROR CLOSING CONNECTION: {e} ======S")       


    # ===============================================================================
    # STARTING TASKS 
    # ===============================================================================
    
    for table in ENABLED_TABLES:
        with TaskGroup(group_id=f"{table}") as tg:

            table_tasks = [
                {"table_name": table, "tenant_name": tenant}
                for tenant in TENANTS
            ]

            process_table_tenant.expand_kwargs(table_tasks)

lms_etl_pipeline()


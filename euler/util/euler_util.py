"""
EULER UTILS FOR REPORTS
LAST_DATE : 2026-09-09
"""

import logging
logger = logging.getLogger(__name__)

# JS ============================== GET THE MAXIMUM DATE FROM DUMPS ============================== JS

def get_high_watermark(pg_cursor, source_tables:list):

    subquery = [f'(SELECT MAX({src["date_column"]}) FROM {src["table_name"]})' for src in source_tables]
    joined = ",\n".join(subquery)
    query = f"""
            SELECT LEAST(
                {joined}
            )
            """
    pg_cursor.execute(query)
    result = pg_cursor.fetchone()[0]
    logger.info(f"JS ====== MAXIMUM DATE WHOSE DATA IS AVAILABLE : [{result}] ====== JS")
    return result

# JS =========================== GET THE LAST PROCESSED DATE FROM TRACKING =========================== JS

def get_last_processed_date(pg_cursor,table_name:str):

    query = f"SELECT last_processed_date FROM euler_tracking_table WHERE table_name = %s"
    parameters =(table_name,)
    pg_cursor.execute(query,parameters) 

    result = pg_cursor.fetchone()
    
    if result is None or result[0] is None:
        logger.info("JS ====== LAST PROCESSED DATE NOT AVAILBE : ['1900-01-01'] ====== JS")
        return '1900-01-01'
    
    logger.info(f"JS ====== LAST PROCESSED DATE FETCHED : [{result[0]}] ====== JS")
    return result[0].strftime("%Y-%m-%d")

# JS ============================== DELETE DATA IN CLICKHOUSE ============================== JS

def delete_forward_window(ch_client,dest_database:str,table_name:str,last_processed:str):

    query = f"""
            DELETE FROM "{dest_database}"."{table_name}"
            WHERE report_date > '{last_processed}'
    """
    ch_client.execute(query)
    logger.info(f"JS ====== WINDOW DELETED WHERE report_date > [{last_processed}] ====== JS")

# JS ============================== INSERT DATA IN CLICKHOUSE ============================== JS

def data_insert(pg_cursor,client,dest_database:str,dest_table:str,query:str):

    PG_FETCH_SIZE = 10000
    CH_FLUSH_SIZE = 50000

    pg_cursor.execute(query)

    col_list = [desc[0] for desc in pg_cursor.description]
    col_sql = ", ".join(f'"{col}"' for col in col_list)
    
    insert_query = f"""
        INSERT INTO "{dest_database}"."{dest_table}" 
        ({col_sql})
        VALUES
    """

    buffer = []
    total = 0

    while True:
        rows = pg_cursor.fetchmany(PG_FETCH_SIZE)
        if not rows:
            break
        buffer.extend(rows)

        if len(buffer)>=CH_FLUSH_SIZE:
            client.execute(insert_query,buffer)
            total += len(buffer)
            logger.info(f"JS ====== FLUSHED [{len(buffer)}] | TOTAL -> [{total}] ====== JS")
            buffer = []

    if buffer:
        client.execute(insert_query, buffer)
        total += len(buffer)
        logger.info(f"JS ====== FLUSHED FINAL [{len(buffer)}] | TOTAL -> [{total}] ====== JS")

    return total

# JS ============================== UPDATE TRACKING TABLE ============================== JS

def update_tracking_table(pg_cursor,table_name:str,high_water_mark:str,rows_inserted:int):
    
    query = """
            INSERT INTO euler_tracking_table
                (table_name,last_processed_date,rows_inserted,last_run_at,status)            
            VALUES (%s,%s,%s,NOW(),'SUCCESS')
            ON CONFLICT (table_name) DO UPDATE SET
                last_processed_date = EXCLUDED.last_processed_date,
                rows_inserted = EXCLUDED.rows_inserted,
                last_run_at = NOW(),
                status = 'SUCCESS'
    """
    parameters = (table_name,high_water_mark,rows_inserted)
    pg_cursor.execute(query,parameters)
    pg_cursor.connection.commit()

    logger.info(f"JS ====== TRACKING TABLE UPDATED : last_processed_date : [{high_water_mark}] | rows_inserted : [{rows_inserted}] | FOR [{table_name}] ====== JS")

# JS ============================== UPSERT QUERY ============================== JS

def upsert_query(table_staging:str,destination_table:str,primary_key:list,columns:list):

    primary_key_str = ", ".join(f'"{pk}"' for pk in primary_key)
    columm_str      = ", ".join(f'"{c}"' for c in columns)
    update_column_list = [f'"{col}" = EXCLUDED."{col}"' for col in columns if col not in primary_key]
    update_column_list.append(f'"updated_at" = NOW()')
    update_column_str = ",\n".join(update_column_list)

    query = f"""
    INSERT INTO {destination_table} ({columm_str})
    SELECT DISTINCT ON ({primary_key_str}) {columm_str}
    FROM {table_staging}
    ORDER BY {primary_key_str}, ctid DESC
    ON CONFLICT ({primary_key_str})
    DO UPDATE SET
        {update_column_str}
    """

    return query

# JS ============================== NEW ============================== JS





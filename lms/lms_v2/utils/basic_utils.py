"""
This module handles basic utility functions.
"""

# ============================= Logger Setup ==============================
import logging
logger = logging.getLogger(__name__)
# ==========================================================================


def map_datatype_to_clickhouse(postgres_datatype:int):
    """
    Maps the postgres datatypes to clickhouse datatypes.
    
    Args:
        postgres_datatype (int): postgres datatype 
        Note → (cursor.description[1] is NOT string — it’s a Postgres OID (int))

    Returns:
        str: clickhouse datatype
    """
    mapping = {
        16: "UInt8",
        20: "Int64",
        21: "Int16",
        23: "Int32",
        700: "Float32",
        701: "Float64",
        1700: "Float64",
        1043: "String",
        25: "String",
        1082: "Date",
        1114: "DateTime",
        1184: "DateTime",
    }

    return mapping.get(postgres_datatype,"String")

def get_schema_from_query(pg_cursor,postgres_query:str):
    """
    Gets the column name and datatypes from the query of postgres.
    
    Args:
        pg_cursor: 
        postgres_query (str): query to get the schema from

    Returns:
        list: list of columns with their datatypes
    """

    clean_query = postgres_query.strip().rstrip(";")

    select_query = f"""
    SELECT * FROM ({clean_query}) t LIMIT 0
    """
    try:
        pg_cursor.execute(select_query)
    except Exception as e:
        logger.error(f"J===== FAILED TO GET SCHEMA FROM QUERY =====S {e}")
        raise
        
    columns = [
        f'"{desc[0]}" Nullable({map_datatype_to_clickhouse(desc[1])})'
        for desc in pg_cursor.description
    ]
    
    return columns

def create_table_in_clickhouse(ch_client,database_name:str,table_name:str,columns:list,order_by_column:str="tuple()"):
    """
    Creates the table in clickhouse.
    
    Args:
        ch_client: clickhouse client
        database_name (str): database name
        table_name (str): table name
        columns (list): list of columns with their datatypes
        order_by_column (str): order by column
    """

    columns_sql = ",\n".join(columns)

    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS "{database_name}"."{table_name}"
    (
        {columns_sql}
    )
    ENGINE = MergeTree()
    ORDER BY {order_by_column}
    """

    ch_client.execute(create_table_query)

    logger.info(f"J====== TABLE [{table_name}] CREATED SUCCESSFULLY ======S")

def ensure_clickhouse_table_from_query(
    ch_client,
    pg_cursor,
    postgres_query:str,
    ch_database_name:str,
    table_name:str,
    order_by_column:str="tuple()"
    ):

    """
    Creates the table if it doesn't exists in the database.

    Args:
        ch_client: clickhouse client
        pg_cursor: postgres cursor
        postgres_query (str): query to get the schema from
        ch_database_name (str): database name
        table_name (str): table name
        order_by_column (str): order by column
    """

    logger.info(f"J====== CREATING TABLE [{table_name}] IN DATABASE [{ch_database_name}]======S")

    col_list = get_schema_from_query(pg_cursor,postgres_query)

    logger.info(f"J====== COLUMNS LIST FOR [{table_name}]: {col_list} ======S")

    if not col_list:
        logger.error("J===== FAILED TO GET SCHEMA FROM QUERY =====S")
        raise ValueError("J===== FAILED TO GET SCHEMA FROM QUERY =====S")

    create_table_in_clickhouse(
        ch_client,
        ch_database_name,
        table_name,
        col_list,
        order_by_column
        )




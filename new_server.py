# oracle_crud_server.py
import oracledb
import uuid
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

print("Script started: Loading environment variables for Oracle CRUD Server...", flush=True)

# Initialize the MCP server with a descriptive name for the agent to use
mcp = FastMCP("OracleCRUD")

# --- ORACLE DATABASE CONFIGURATION ---
# These values are loaded from your .env file.
# Ensure your .env file contains:
# DB_USER="SYSTEM"
# DB_PASSWORD="YOUR_SYSTEM_PASSWORD" (replace with your actual password)
# DB_HOST="localhost"
# DB_PORT="1521"
# DB_SERVICE_NAME="XE"
DB_CONFIG = {
    "user": "SYSTEM",
    "password": "qwertyuiop",
    "host": "localhost",
    "port": 1521,
    "service_name": "XE"
}

print(f"DEBUG: DB_CONFIG loaded: User={DB_CONFIG['user']}, Host={DB_CONFIG['host']},"
      f" Port={DB_CONFIG['port']}, Service={DB_CONFIG['service_name']}", flush=True)

def get_db_connection():
    """
    Establishes and returns a new Oracle database connection using the configured credentials.
    This function is called by each tool before performing database operations.

    Returns:
        oracledb.Connection: A new connection object if successful.
        None: If a connection error occurs.
    Raises:
        oracledb.Error: If a specific Oracle database error occurs during connection.
        Exception: For any other unexpected errors during connection.
    """
    print("Attempting to get DB connection...", flush=True)
    try:
        connection = oracledb.connect(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            service_name=DB_CONFIG["service_name"]
        )
        print("Successfully connected to Oracle Database.", flush=True)
        return connection
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to connect to Oracle Database: {error_obj.message}", file=sys.stderr, flush=True)
        raise # Re-raise the exception to propagate the error
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during DB connection: {e}", file=sys.stderr, flush=True)
        raise # Re-raise other exceptions too

@mcp.tool()
def create_record(table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a new record (row) in the specified Oracle database table.
    This tool is suitable for adding new entries like users, products, or any other entity.

    Args:
        table_name (str): The name of the table where the new record should be inserted.
                          This name MUST match the actual table name in your Oracle database,
                          typically in uppercase (e.g., "USERS", "PRODUCTS", "ORDERS").
                          The tool will automatically convert it to uppercase.
        data (Dict[str, Any]): A dictionary representing the new record's data.
                               - Keys: Must be the exact column names in the target table.
                                       These will be converted to uppercase automatically.
                               - Values: The actual data for each column.
                                       DO NOT provide SQL data types (e.g., 'VARCHAR2', 'NUMBER') as values.
                                       Provide the actual value (e.g., "Alice", 30, 1200.50).
                               - 'ID' Column: If your table has an 'ID' column (recommended for primary keys),
                                            and you don't provide it in 'data', a UUID (Universally Unique Identifier)
                                            will be automatically generated and assigned to the 'ID' column.
                                            If you provide an 'ID', it will be used.

    Returns:
        Dict[str, Any]: On success, returns a dictionary containing the complete created record,
                        including the 'ID' (whether provided or auto-generated).
                        Example: {"ID": "uuid-123", "NAME": "Alice", "EMAIL": "alice@example.com", "AGE": 30}
        Dict[str, Any]: On failure, returns a dictionary with an "error" key detailing the problem,
                        and potentially "sql" and "data" keys for debugging.
                        Example: {"error": "Database Error: ORA-00001: unique constraint violated", "sql": "...", "data": {...}}
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Failed to establish database connection."}

        cursor = conn.cursor()
        table_name_upper = table_name.upper()

        record_id = data.get("ID", str(uuid.uuid4()))
        data["ID"] = record_id # Ensure ID is part of the data dictionary for insertion
        
        # Convert all keys in data to uppercase to match Oracle column names
        processed_data = {k.upper(): v for k, v in data.items()}

        columns = ", ".join(processed_data.keys())
        placeholders = ", ".join([f":{key}" for key in processed_data.keys()])
        sql = f"INSERT INTO {table_name_upper} ({columns}) VALUES ({placeholders})"

        print(f"DEBUG: Executing CREATE SQL: {sql}", flush=True)
        print(f"DEBUG: With bind variables: {processed_data}", flush=True)

        cursor.execute(sql, processed_data)
        conn.commit() # Commit the transaction to make changes permanent
        print(f"SUCCESS: Created record in '{table_name_upper}': ID={record_id}, Data={data}", flush=True)
        return {"ID": record_id, **data}
    except oracledb.Error as e:
        error_obj, = e.args
        error_message = f"Database Error: {error_obj.message}"
        print(f"ERROR: Failed to create record in '{table_name_upper}': {error_message}", file=sys.stderr, flush=True)
        if conn:
            conn.rollback() # Rollback changes on error
        return {"error": error_message, "sql": sql, "data": processed_data}
    except Exception as e:
        error_message = f"Unexpected Error: {e}"
        print(f"ERROR: An unexpected error occurred in create_record: {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "sql": sql, "data": processed_data}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@mcp.tool()
def read_records(table_name: str, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Reads one or more records (rows) from the specified Oracle database table.
    This tool is ideal for retrieving information about existing entities.

    Args:
        table_name (str): The name of the table to read from (e.g., "USERS", "PRODUCTS", "ORDERS").
                          This name MUST match the actual table name in your Oracle database,
                          typically in uppercase. The tool will automatically convert it to uppercase.
        query (Optional[Dict[str, Any]]): An optional dictionary used to filter the records.
                                          - If `None` or an empty dictionary (`{}`): All records from the `table_name` will be returned.
                                          - Keys: Must be the exact column names in the target table (e.g., "NAME", "AGE", "EMAIL", "CATEGORY", "ID").
                                                  These will be converted to uppercase automatically.
                                          - Values: The specific filter criteria for each column.
                                          - **CRITICAL:** DO NOT provide raw SQL queries (e.g., "SELECT * FROM users" or "WHERE name = 'Alice'") here.
                                                    This parameter expects a Python dictionary for structured filtering ONLY.

    Returns:
        List[Dict[str, Any]]: On success, returns a list of dictionaries. Each dictionary represents a
                              matching record, with keys as uppercase column names and values as the record data.
                              Returns an empty list (`[]`) if no records match the query or if the table is empty.
                              Example (for users): [{"ID": "uuid-1", "NAME": "Alice", "EMAIL": "a@ex.com", "AGE": 30}]
        Dict[str, Any]: On failure, returns a dictionary with an "error" key detailing the problem,
                        and potentially "sql" and "query" keys for debugging.
                        Example: {"error": "Database Error: ORA-00942: table or view does not exist", "sql": "...", "query": {...}}
    """
    conn = None
    cursor = None
    records = []
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Failed to establish database connection."}

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        sql = f"SELECT * FROM {table_name_upper}"
        bind_vars = {}

        # Validate and process the 'query' parameter
        if isinstance(query, str) and not query: # Treat empty string as no query
            query = None
        elif isinstance(query, str) and query: # If LLM provides a non-empty string, it's an invalid usage
            raise ValueError("The 'query' parameter must be a dictionary for filtering (e.g., {'NAME': 'Alice'}), not a raw SQL string.")
        elif query is not None and not isinstance(query, dict): # If it's not None and not a dict
            raise ValueError("The 'query' parameter must be a dictionary or None for filtering.")

        if query: # If a valid query dictionary is provided
            where_clauses = []
            processed_query = {k.upper(): v for k, v in query.items()}
            for key, value in processed_query.items():
                where_clauses.append(f"{key} = :{key}")
                bind_vars[key] = value
            sql += " WHERE " + " AND ".join(where_clauses)

        print(f"DEBUG: Executing READ SQL: {sql}", flush=True)
        print(f"DEBUG: With bind variables: {bind_vars}", flush=True)

        cursor.execute(sql, bind_vars)
        
        column_names = [desc[0] for desc in cursor.description] # Get column names from cursor description
        
        for row in cursor:
            record = {}
            for i, col_name in enumerate(column_names):
                record[col_name] = row[i]
            records.append(record)

        print(f"SUCCESS: Read {len(records)} records from '{table_name_upper}' with query {query}: {records}", flush=True)
        return records
    except oracledb.Error as e:
        error_obj, = e.args
        error_message = f"Database Error: {error_obj.message}"
        print(f"ERROR: Failed to read records from '{table_name_upper}': {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "sql": sql, "query": query}
    except ValueError as e: # Catch the explicit ValueError we raised for invalid query type
        error_message = f"Tool Usage Error: {e}"
        print(f"ERROR: {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "query_provided": query}
    except Exception as e:
        error_message = f"Unexpected Error: {e}"
        print(f"ERROR: An unexpected error occurred in read_records: {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "sql": sql, "query": query}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@mcp.tool()
def update_record(table_name: str, record_id: str, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates an existing record (row) in the specified Oracle table by its unique ID.
    This tool is used to modify existing entries, such as changing a user's age or a product's price.

    Args:
        table_name (str): The name of the table where the record to update resides.
                          This name MUST match the actual table name in your Oracle database,
                          typically in uppercase (e.g., "USERS", "PRODUCTS").
                          The tool will automatically convert it to uppercase.
        record_id (str): The unique identifier (ID) of the record to be updated.
                         This must be the exact value from the 'ID' column of the target record.
        new_data (Dict[str, Any]): A dictionary containing the column(s) to update and their new values.
                                   - Keys: Must be the exact column names in the target table (e.g., "AGE", "EMAIL", "PRICE").
                                           These will be converted to uppercase automatically.
                                   - Values: The new data for the specified columns.
                                   - If this dictionary is empty, no update will occur.

    Returns:
        Optional[Dict[str, Any]]: On success, returns a dictionary representing the updated record.
                                  This is retrieved by performing a `read_records` call after the update.
                                  Returns `None` if the record with the given `record_id` was not found.
        Dict[str, Any]: On failure, returns a dictionary with an "error" key detailing the problem,
                        and potentially "sql", "record_id", and "new_data" keys for debugging.
                        Example: {"error": "Database Error: ORA-01407: cannot update (...) to NULL", "sql": "...", "record_id": "...", "new_data": {...}}
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Failed to establish database connection."}

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        
        set_clauses = []
        bind_vars = {"ID_TO_UPDATE": record_id} # Bind variable for the WHERE clause
        
        # Convert all keys in new_data to uppercase to match Oracle column names
        processed_new_data = {k.upper(): v for k, v in new_data.items()}
        for key, value in processed_new_data.items():
            set_clauses.append(f"{key} = :{key}") # e.g., "AGE = :AGE"
            bind_vars[key] = value # Add new data values to bind variables

        if not set_clauses:
            print("WARNING: No data provided for update.", flush=True)
            return None

        sql = f"UPDATE {table_name_upper} SET {', '.join(set_clauses)} WHERE ID = :ID_TO_UPDATE"

        print(f"DEBUG: Executing UPDATE SQL: {sql}", flush=True)
        print(f"DEBUG: With bind variables: {bind_vars}", flush=True)

        cursor.execute(sql, bind_vars)
        conn.commit() # Commit the transaction

        if cursor.rowcount > 0:
            print(f"SUCCESS: Updated record with ID '{record_id}' in '{table_name_upper}'.", flush=True)
            # Re-read the updated record to ensure the returned data is fresh and accurate
            updated_record = read_records(table_name_upper, {"ID": record_id})
            return updated_record[0] if updated_record else None
        else:
            print(f"INFO: Record with ID '{record_id}' not found in table '{table_name_upper}'.", flush=True)
            return None
    except oracledb.Error as e:
        error_obj, = e.args
        error_message = f"Database Error: {error_obj.message}"
        print(f"ERROR: Failed to update record in '{table_name_upper}': {error_message}", file=sys.stderr, flush=True)
        if conn:
            conn.rollback()
        return {"error": error_message, "sql": sql, "record_id": record_id, "new_data": new_data}
    except Exception as e:
        error_message = f"Unexpected Error: {e}"
        print(f"ERROR: An unexpected error occurred in update_record: {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "sql": sql, "record_id": record_id, "new_data": new_data}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@mcp.tool()
def delete_record(table_name: str, record_id: str) -> bool:
    """
    Deletes a single record (row) from the specified Oracle table by its unique ID.
    This tool is used to remove entries from the database.

    Args:
        table_name (str): The name of the table from which the record should be deleted.
                          This name MUST match the actual table name in your Oracle database,
                          typically in uppercase (e.g., "USERS", "PRODUCTS").
                          The tool will automatically convert it to uppercase.
        record_id (str): The unique identifier (ID) of the record to be deleted.
                         This must be the exact value from the 'ID' column of the target record.

    Returns:
        bool: Returns `True` if the record was successfully deleted (i.e., one row was affected).
              Returns `False` if the record with the given `record_id` was not found in the table.
        Dict[str, Any]: On failure, returns a dictionary with an "error" key detailing the problem,
                        and potentially "sql" and "record_id" keys for debugging.
                        Example: {"error": "Database Error: ORA-02292: integrity constraint violated", "sql": "...", "record_id": "..."}
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Failed to establish database connection."}

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        sql = f"DELETE FROM {table_name_upper} WHERE ID = :record_id"

        print(f"DEBUG: Executing DELETE SQL: {sql}", flush=True)
        print(f"DEBUG: With bind variables: {{'record_id': '{record_id}'}}", flush=True)

        cursor.execute(sql, {"record_id": record_id})
        conn.commit() # Commit the transaction

        if cursor.rowcount > 0:
            print(f"SUCCESS: Deleted record with ID '{record_id}' from table '{table_name_upper}'.", flush=True)
            return True
        else:
            print(f"INFO: Record with ID '{record_id}' not found in table '{table_name_upper}'.", flush=True)
            return False
    except oracledb.Error as e:
        error_obj, = e.args
        error_message = f"Database Error: {error_obj.message}"
        print(f"ERROR: Failed to delete record from '{table_name_upper}': {error_message}", file=sys.stderr, flush=True)
        if conn:
            conn.rollback()
        return {"error": error_message, "sql": sql, "record_id": record_id}
    except Exception as e:
        error_message = f"Unexpected Error: {e}"
        print(f"ERROR: An unexpected error occurred in delete_record: {error_message}", file=sys.stderr, flush=True)
        return {"error": error_message, "sql": sql, "record_id": record_id}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting Oracle CRUD MCP server. This server will connect to your local Oracle XE database.", flush=True)
    print("Ensure you have configured DB_CONFIG in your .env file with your correct credentials and have created the necessary tables.", flush=True)
    try:
        # Explicitly test the database connection at startup
        with get_db_connection() as initial_conn:
            print("Initial database connection successful during server startup.", flush=True)
        mcp.run(transport="stdio") # Starts the MCP server, listening for tool calls
    except Exception as e:
        print(f"MCP Server encountered an error during startup or runtime: {e}", file=sys.stderr, flush=True)
    print("MCP Server process finished.", flush=True)

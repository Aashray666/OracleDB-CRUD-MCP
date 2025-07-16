import os
from typing import Literal, Union, List, Dict, Any
import oracledb
from pydantic import BaseModel, Field
import sys
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8") # Keep this, it's good practice

# Load environment variables (though you're hardcoding, it doesn't hurt)
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP(
    name="OracleDatabaseManager",
    description="A server to connect and manage an Oracle XE database, providing tools to execute SQL queries."
)

# Database connection details (hardcoded)
DB_USER = "myagent"
DB_PASSWORD = "myagent123"
DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE_NAME = "XEPDB1" # Confirmed to be your PDB service name

try:
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, service_name=DB_SERVICE_NAME)
    conn.close()
    print("Successfully connected to Oracle XE database during startup check.", flush=True) # <<< ADDED FLUSH
except oracledb.Error as e:
    print(f"Error connecting to Oracle XE database: {e}", flush=True) # <<< ADDED FLUSH
    print("Please ensure your Oracle XE database is running and the connection details are correct.", flush=True) # <<< ADDED FLUSH
    exit(1)
except Exception as e: # Catch generic exceptions during initial connection
    print(f"An unexpected error occurred during initial DB connection check: {e}", flush=True) # <<< ADDED FLUSH
    exit(1)


# Pydantic model and execute_sql_query tool remain the same
class SQLQueryResult(BaseModel):
    """Represents the result of an SQL query execution."""
    status: Literal["success", "failed"] = Field(description="Status of the SQL query execution.")
    message: str = Field(description="A message describing the outcome of the query.")
    rows_affected: Union[int, None] = Field(None, description="Number of rows affected by DML statements (INSERT, UPDATE, DELETE).")
    data: Union[List[Dict[str, Any]], None] = Field(None, description="List of dictionaries, where each dictionary represents a row with column names as keys. Only for SELECT queries.")
    columns: Union[List[str], None] = Field(None, description="List of column names for SELECT query results.")


@mcp.tool()
def execute_sql_query(query: str) -> SQLQueryResult:
    connection = None
    cursor = None
    try:
        connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, service_name=DB_SERVICE_NAME)
        cursor = connection.cursor()

        cursor.execute(query)

        if query.strip().upper().startswith("SELECT"):
            columns = [col[0] for col in cursor.description]
            rows = []
            for row in cursor:
                rows.append(dict(zip(columns, row)))
            return SQLQueryResult(
                status="success",
                message="Query executed successfully.",
                data=rows,
                columns=columns
            )
        else:
            connection.commit()
            rows_affected = cursor.rowcount
            return SQLQueryResult(
                status="success",
                message="Query executed successfully.",
                rows_affected=rows_affected
            )

    except oracledb.Error as e:
        error_message = f"Oracle Database Error: {e}"
        if connection:
            connection.rollback()
        return SQLQueryResult(
            status="failed",
            message=error_message
        )
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        if connection:
            connection.rollback()
        return SQLQueryResult(
            status="failed",
            message=error_message
        )
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    print("Starting FastMCP Oracle Database Manager server...", flush=True) # <<< ADDED FLUSH
    mcp.run()
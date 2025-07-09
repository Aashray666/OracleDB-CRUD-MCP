# direct_oracle_crud_hardcoded.py
import oracledb
import uuid
from typing import Dict, Any, List, Optional

# --- ORACLE DATABASE CONFIGURATION (HARDCODED) ---
# IMPORTANT: Replace "YOUR_SYSTEM_PASSWORD" with your actual SYSTEM user password.
# This is for testing purposes only and NOT recommended for production.
DB_CONFIG = {
    "user": "SYSTEM",
    "password": "qwertyuiop",
    "host": "localhost",
    "port": 1521,
    "service_name": "XE"
}

def get_db_connection():
    """Establishes and returns a new Oracle database connection."""
    try:
        connection = oracledb.connect(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            service_name=DB_CONFIG["service_name"]
        )
        print("Successfully connected to Oracle Database.")
        return connection
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to connect to Oracle Database: {error_obj.message}")
        return None # Return None if connection fails

def create_record(table_name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Creates a new record in the specified Oracle table.
    Generates a UUID for the 'ID' field if not provided.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return None

        cursor = conn.cursor()
        table_name_upper = table_name.upper() # Ensure table name is uppercase for Oracle

        record_id = data.get("ID", str(uuid.uuid4()))
        data["ID"] = record_id
        processed_data = {k.upper(): v for k, v in data.items()} # Ensure column names are uppercase

        columns = ", ".join(processed_data.keys())
        placeholders = ", ".join([f":{key}" for key in processed_data.keys()])
        sql = f"INSERT INTO {table_name_upper} ({columns}) VALUES ({placeholders})"

        print(f"DEBUG: Executing CREATE SQL: {sql}")
        print(f"DEBUG: With bind variables: {processed_data}")

        cursor.execute(sql, processed_data)
        conn.commit()
        print(f"SUCCESS: Created record in '{table_name_upper}': ID={record_id}, Data={data}")
        return {"ID": record_id, **data}
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to create record in '{table_name_upper}': {error_obj.message}")
        if conn: conn.rollback()
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def read_records(table_name: str, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Reads records from the specified Oracle table.
    """
    conn = None
    cursor = None
    records = []
    try:
        conn = get_db_connection()
        if not conn: return []

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        sql = f"SELECT * FROM {table_name_upper}"
        bind_vars = {}

        if query:
            where_clauses = []
            processed_query = {k.upper(): v for k, v in query.items()}
            for key, value in processed_query.items():
                where_clauses.append(f"{key} = :{key}")
                bind_vars[key] = value
            sql += " WHERE " + " AND ".join(where_clauses)

        print(f"DEBUG: Executing READ SQL: {sql}")
        print(f"DEBUG: With bind variables: {bind_vars}")

        cursor.execute(sql, bind_vars)
        
        column_names = [desc[0] for desc in cursor.description]
        for row in cursor:
            record = {}
            for i, col_name in enumerate(column_names):
                record[col_name] = row[i]
            records.append(record)

        print(f"SUCCESS: Read {len(records)} records from '{table_name_upper}'.")
        return records
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to read records from '{table_name_upper}': {error_obj.message}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_record(table_name: str, record_id: str, new_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates an existing record in the specified Oracle table by its ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return None

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        
        set_clauses = []
        bind_vars = {"ID_TO_UPDATE": record_id}
        processed_new_data = {k.upper(): v for k, v in new_data.items()}
        for key, value in processed_new_data.items():
            set_clauses.append(f"{key} = :{key}")
            bind_vars[key] = value

        if not set_clauses:
            print("WARNING: No data provided for update.")
            return None

        sql = f"UPDATE {table_name_upper} SET {', '.join(set_clauses)} WHERE ID = :ID_TO_UPDATE"

        print(f"DEBUG: Executing UPDATE SQL: {sql}")
        print(f"DEBUG: With bind variables: {bind_vars}")

        cursor.execute(sql, bind_vars)
        conn.commit()

        if cursor.rowcount > 0:
            print(f"SUCCESS: Updated record with ID '{record_id}' in '{table_name_upper}'.")
            # Re-read the updated record to return it
            return read_records(table_name_upper, {"ID": record_id})[0]
        else:
            print(f"INFO: Record with ID '{record_id}' not found in table '{table_name_upper}'.")
            return None
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to update record in '{table_name_upper}': {error_obj.message}")
        if conn: conn.rollback()
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def delete_record(table_name: str, record_id: str) -> bool:
    """
    Deletes a record from the specified Oracle table by its ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn: return False

        cursor = conn.cursor()
        table_name_upper = table_name.upper()
        sql = f"DELETE FROM {table_name_upper} WHERE ID = :record_id"

        print(f"DEBUG: Executing DELETE SQL: {sql}")
        print(f"DEBUG: With bind variables: {{'record_id': '{record_id}'}}")

        cursor.execute(sql, {"record_id": record_id})
        conn.commit()

        if cursor.rowcount > 0:
            print(f"SUCCESS: Deleted record with ID '{record_id}' from table '{table_name_upper}'.")
            return True
        else:
            print(f"INFO: Record with ID '{record_id}' not found in table '{table_name_upper}'.")
            return False
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"ERROR: Failed to delete record from '{table_name_upper}': {error_obj.message}")
        if conn: conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    print("\n--- Starting Complete Direct Oracle CRUD Operations (Hardcoded Credentials) ---")

    # --- Test Case 1: Create a user record ---
    print("\n--- Creating 'Alice' ---")
    alice_data = {"NAME": "amit", "EMAIL": "amit@example.com", "AGE": 30}
    created_alice = create_record("USERS", alice_data)
    alice_id = created_alice["ID"] if created_alice else None

    # --- Test Case 2: Create another user record ---
    print("\n--- Creating 'Bob' ---")
    bob_data = {"NAME": "Bob", "EMAIL": "bob@example.com", "AGE": 25}
    created_bob = create_record("USERS", bob_data)
    bob_id = created_bob["ID"] if created_bob else None

    # --- Test Case 3: Read all user records ---
    print("\n--- Reading all users ---")
    all_users = read_records("USERS")
    print(f"All users data: {all_users}")

    # --- Test Case 4: Read a specific user by name ---
    print("\n--- Reading user 'Alice' by name ---")
    alice_from_db = read_records("USERS", {"NAME": "Alice"})
    print(f"Alice from DB: {alice_from_db}")

    # --- Test Case 5: Update Alice's age ---
    if alice_id:
        print(f"\n--- Updating Alice (ID: {alice_id}) ---")
        updated_alice = update_record("USERS", alice_id, {"AGE": 31, "EMAIL": "alice.new@example.com"})
        print(f"Updated Alice data: {updated_alice}")
    else:
        print("\n--- Skipping Update Alice (ID not found) ---")

    # --- Test Case 6: Read all users again to see update ---
    print("\n--- Reading all users after update ---")
    all_users_after_update = read_records("USERS")
    print(f"All users after update: {all_users_after_update}")

    # --- Test Case 7: Create a product record ---
    print("\n--- Creating a product 'Laptop' ---")
    laptop_data = {"NAME": "Laptop", "PRICE": 1200.50, "CATEGORY": "ELECTRONICS"}
    created_laptop = create_record("PRODUCTS", laptop_data)
    laptop_id = created_laptop["ID"] if created_laptop else None

    # --- Test Case 8: Read all products ---
    print("\n--- Reading all products ---")
    all_products = read_records("PRODUCTS")
    print(f"All products data: {all_products}")

    # --- Test Case 9: Read products by category ---
    print("\n--- Reading 'ELECTRONICS' products ---")
    electronics_products = read_records("PRODUCTS", {"CATEGORY": "ELECTRONICS"})
    print(f"Electronics products: {electronics_products}")

    # --- Test Case 10: Delete Alice ---
    if alice_id:
        print(f"\n--- Deleting Alice (ID: {alice_id}) ---")
        deleted_alice = delete_record("USERS", alice_id)
        print(f"Alice deleted status: {deleted_alice}")
    else:
        print("\n--- Skipping Delete Alice (ID not found) ---")

    # --- Test Case 11: Verify Alice is deleted ---
    print("\n--- Verifying Alice deletion ---")
    alice_after_delete = read_records("USERS", {"NAME": "Alice"})
    print(f"Alice after delete: {alice_after_delete}")

    # --- Test Case 12: Delete Bob ---
    if bob_id:
        print(f"\n--- Deleting Bob (ID: {bob_id}) ---")
        deleted_bob = delete_record("USERS", bob_id)
        print(f"Bob deleted status: {deleted_bob}")
    else:
        print("\n--- Skipping Delete Bob (ID not found) ---")

    print("\n--- Complete Direct Oracle CRUD Operations Finished ---")

# test_oracle_connection.py
import oracledb
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "service_name": os.getenv("DB_SERVICE_NAME")
}

try:
    print("Attempting to connect to Oracle Database...")
    with oracledb.connect(
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        service_name=DB_CONFIG["service_name"]
    ) as connection:
        print("Successfully connected to Oracle Database!")
        with connection.cursor() as cursor:
            cursor.execute("SELECT SYSDATE FROM DUAL")
            sysdate, = cursor.fetchone()
            print(f"Current database date: {sysdate}")

except oracledb.Error as e:
    error_obj, = e.args
    print(f"Error connecting to Oracle Database: {error_obj.message}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


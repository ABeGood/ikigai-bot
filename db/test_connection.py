import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# Get the database URL from .env
db_url = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f"Successfully connected! PostgreSQL version: {db_version[0]}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import connection, cursor
from typing import Optional

load_dotenv()

# SQL for creating the reservations table
# Updated table creation SQL with new schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    order_id VARCHAR UNIQUE,
    telegram_id VARCHAR,
    name VARCHAR,
    type VARCHAR,
    place INTEGER,
    period FLOAT,
    day DATE,
    time_from TIMESTAMP WITH TIME ZONE,
    time_to TIMESTAMP WITH TIME ZONE,
    sum FLOAT,
    payed BOOLEAN,
    payment_confirmation_link VARCHAR,
    payment_confirmation_file_id VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_order_id ON reservations(order_id);
"""

MIGRATE_TIME_TABLE_SQL = """
-- 1. First create new columns
ALTER TABLE reservations 
ADD COLUMN time_from_new TIME,
ADD COLUMN time_to_new TIME;

-- 2. Drop old problematic columns
ALTER TABLE reservations 
DROP COLUMN time_from,
DROP COLUMN time_to;

-- 3. Rename new columns
ALTER TABLE reservations 
RENAME COLUMN time_from_new TO time_from;

ALTER TABLE reservations 
RENAME COLUMN time_to_new TO time_to;
"""

MIGRATE_TIMESTAMP_WITH_TIME_TABLE_SQL = """
-- 1. First create new datetime columns
ALTER TABLE reservations 
ADD COLUMN time_from_new TIMESTAMP WITH TIME ZONE,
ADD COLUMN time_to_new TIMESTAMP WITH TIME ZONE;

-- 2. Drop old time columns
ALTER TABLE reservations 
DROP COLUMN time_from,
DROP COLUMN time_to;

-- 3. Rename new columns
ALTER TABLE reservations 
RENAME COLUMN time_from_new TO time_from;

ALTER TABLE reservations 
RENAME COLUMN time_to_new TO time_to;
"""

TRUNCATE_TABLE_SQL = "TRUNCATE TABLE reservations RESTART IDENTITY;"
DROP_TABLE_SQL = "DROP TABLE IF EXISTS reservations;"

def get_db_connection() -> connection:
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

def clear_table(conn: Optional[connection] = None) -> bool:
    """Delete all records from the reservations table but keep the structure"""
    should_close_conn = conn is None
    try:
        if conn is None:
            conn = get_db_connection()
        
        cur = conn.cursor()
        cur.execute(TRUNCATE_TABLE_SQL)
        conn.commit()
        print("Successfully cleared all records from reservations table")
        return True
        
    except Exception as e:
        print(f"Error clearing table: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if should_close_conn and conn:
            conn.close()

def reset_table(conn: Optional[connection] = None) -> bool:
    """Drop and recreate the reservations table"""
    should_close_conn = conn is None
    try:
        if conn is None:
            conn = get_db_connection()
            
        cur = conn.cursor()
        cur.execute(DROP_TABLE_SQL)
        cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        print("Successfully reset reservations table")
        return True
        
    except Exception as e:
        print(f"Error resetting table: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if should_close_conn and conn:
            conn.close()

if __name__ == "__main__":
    # Example usage
    try:
        conn = get_db_connection()
        
        # Choose one of these operations:
        # clear_table(conn)  # Just delete all records
        reset_table(conn)  # Drop and recreate table
        
    except Exception as e:
        print(f"Operation failed: {e}")
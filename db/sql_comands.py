import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# SQL for creating the reservations table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reservations (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    order_id VARCHAR UNIQUE,
    telegram_id VARCHAR,
    name VARCHAR,
    type VARCHAR,
    place INTEGER,
    day DATE,
    time_from TIME,
    time_to TIME,
    period INTEGER,
    payed VARCHAR
);
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

try:
    # Connect to your Railway database
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # Create the table
    cursor.execute(MIGRATE_TIMESTAMP_WITH_TIME_TABLE_SQL)
    
    # Commit the changes
    conn.commit()
    print("Migrated successfully!")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
import sqlite3
import os

DB_PATH = "portfolio_v2.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add geography to transaction table
        print("Adding geography column to transaction table...")
        cursor.execute('ALTER TABLE "transaction" ADD COLUMN geography TEXT DEFAULT "India"')
        
        # Add geography to holding table
        print("Adding geography column to holding table...")
        cursor.execute('ALTER TABLE "holding" ADD COLUMN geography TEXT DEFAULT "India"')
        
        conn.commit()
        print("Migration completed successfully!")
    except sqlite3.OperationalError as e:
        if "duplicate column name: geography" in str(e).lower():
            print("Migration already applied: geography column exists.")
        else:
            print(f"Operational error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

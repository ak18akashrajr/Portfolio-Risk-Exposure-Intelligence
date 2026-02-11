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
        # Add category to transaction table
        print("Adding category column to transaction table...")
        try:
            cursor.execute('ALTER TABLE "transaction" ADD COLUMN category TEXT DEFAULT "Equity(Stocks)"')
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("Category column already exists in transaction table.")
            else:
                raise e
        
        # Add category to holding table
        print("Adding category column to holding table...")
        try:
            cursor.execute('ALTER TABLE "holding" ADD COLUMN category TEXT DEFAULT "Equity(Stocks)"')
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("Category column already exists in holding table.")
            else:
                raise e
        
        # Update existing data
        print("Updating GOLDBEES to Commodity...")
        cursor.execute("UPDATE \"transaction\" SET category = 'Commodity' WHERE symbol = 'GOLDBEES'")
        cursor.execute("UPDATE \"holding\" SET category = 'Commodity' WHERE symbol = 'GOLDBEES'")
        
        conn.commit()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

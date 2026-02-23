import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "portfolio_v2.db")

def migrate():
    print(f"Migrating database: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Add folio_number to transaction table
    try:
        cursor.execute('ALTER TABLE "transaction" ADD COLUMN folio_number TEXT')
        print("Added 'folio_number' column to 'transaction' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("'folio_number' already exists in 'transaction' table.")
        else:
            print(f"Error adding column to 'transaction': {e}")
            
    # Add folio_number to holding table
    try:
        cursor.execute("ALTER TABLE holding ADD COLUMN folio_number TEXT")
        print("Added 'folio_number' column to 'holding' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("'folio_number' already exists in 'holding' table.")
        else:
            print(f"Error adding column to 'holding': {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()

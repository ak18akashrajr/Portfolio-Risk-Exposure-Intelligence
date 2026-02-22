import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "portfolio_v2.db")

def check_symbols():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, stock_name FROM holding")
    rows = cursor.fetchall()
    for symbol, name in rows:
        print(f"Symbol: {symbol} | Name: {name}")
    conn.close()

if __name__ == "__main__":
    check_symbols()

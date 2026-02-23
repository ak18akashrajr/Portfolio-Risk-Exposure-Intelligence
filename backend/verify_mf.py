import os
import sys
from sqlmodel import Session, select, text
from backend.database import engine
from backend.models import Transaction, Holding
from backend.ingestion import ingest_excel
import pandas as pd

def verify():
    # Clear existing MF data for a clean test
    with Session(engine) as session:
        print("Clearing existing Mutual Fund data...")
        session.exec(text("DELETE FROM 'transaction' WHERE category = 'Mutual Fund'"))
        session.exec(text("DELETE FROM holding WHERE category = 'Mutual Fund'"))
        session.commit()

    # Ensure we are working with Mutual Fund data
    mf_holdings_path = "holdings_transactions/Mutual_Funds_1551826140_07-02-2026_07-02-2026.xlsx"
    mf_orders_path = "holdings_transactions/Mutual_Funds_Order_History_01-04-2025_07-02-2026.xlsx"
    
    print("Ingesting Mutual Fund Order History...")
    ingest_excel(mf_orders_path)
    
    print("Ingesting Mutual Fund Holdings...")
    ingest_excel(mf_holdings_path)
    
    with Session(engine) as session:
        transactions = session.exec(select(Transaction).where(Transaction.category == "Mutual Fund")).all()
        print(f"Found {len(transactions)} Mutual Fund transactions.")
        
        holdings = session.exec(select(Holding).where(Holding.category == "Mutual Fund")).all()
        print(f"Found {len(holdings)} Mutual Fund holdings.")
        
        for h in holdings:
            print(f"Holding: {h.stock_name}, Folio: {h.folio_number}, Qty: {h.quantity}, Avg Price: {h.avg_price}")

if __name__ == "__main__":
    # Add project root to sys.path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    verify()

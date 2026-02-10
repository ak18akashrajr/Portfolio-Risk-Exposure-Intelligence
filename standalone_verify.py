import sys
import os
import pandas as pd
from sqlmodel import Session, select

# Add current directory to path
sys.path.append(os.getcwd())

from backend.database import create_db_and_tables, engine
from backend.ingestion import ingest_excel
from backend.models import Transaction, Holding

def verify_weighted_average():
    print("Initializing Database...")
    create_db_and_tables()
    
    file_path = r"holdings_transactions\Stocks_Order_History_1551826140_01-04-2021_06-02-2026.xlsx"
    print(f"Processing: {file_path}")
    
    try:
        # Clear existing data if any (for clean test)
        with Session(engine) as session:
            session.exec(select(Transaction)).all()
            # In a real test we might want to drop but here we just append
        
        ingest_excel(file_path)
        print("✓ Ingestion successful!")
        
        with Session(engine) as session:
            holdings = session.exec(select(Holding)).all()
            print(f"\nFound {len(holdings)} holdings in database.\n")
            
            # Print sample to verify logic
            for h in holdings[:10]:
                print(f"Stock: {h.stock_name} ({h.symbol})")
                print(f"  ISIN: {h.isin}")
                print(f"  Qty: {h.quantity}")
                print(f"  Avg Buy Price (Weighted): ₹{h.avg_price:.2f}")
                print(f"  Current Invested (Cost): ₹{h.total_invested:.2f}")
                print(f"  Last Activity: {h.last_transaction_date}")
                print("-" * 20)
                
            # Verify a specific example if possible (e.g. PNB or ETERNAL)
            for h in holdings:
                if h.symbol == 'PNB':
                    print(f"Verification Check for PNB:")
                    print(f"  Qty: {h.quantity}, Avg: {h.avg_price:.2f}, Total: {h.total_invested:.2f}")

    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_weighted_average()

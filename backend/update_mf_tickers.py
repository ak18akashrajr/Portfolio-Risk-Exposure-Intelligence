from sqlmodel import Session, select
from backend.database import engine
from backend.models import Transaction, Holding
from backend.ingestion import MF_TICKER_MAP

def update_tickers():
    print("Starting Mutual Fund ticker migration...")
    with Session(engine) as session:
        # 1. Update Transactions
        transactions = session.exec(select(Transaction).where(Transaction.category == "Mutual Fund")).all()
        tx_count = 0
        for tx in transactions:
            if tx.symbol in MF_TICKER_MAP:
                tx.symbol = MF_TICKER_MAP[tx.symbol]
                session.add(tx)
                tx_count += 1
        
        # 2. Update Holdings
        holdings = session.exec(select(Holding).where(Holding.category == "Mutual Fund")).all()
        h_count = 0
        for h in holdings:
            if h.symbol in MF_TICKER_MAP:
                h.symbol = MF_TICKER_MAP[h.symbol]
                session.add(h)
                h_count += 1
        
        session.commit()
        print(f"Updated {tx_count} transactions and {h_count} holdings with correct Yahoo Finance tickers.")

if __name__ == "__main__":
    update_tickers()

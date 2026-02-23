from backend.database import engine, Session
from backend.models import Transaction, Holding
from backend.ingestion import update_holdings
from sqlmodel import SQLModel, select, text

def reset_and_sync():
    print("Dropping existing 'holding' table...")
    with engine.connect() as conn:
        conn.execute(text('DROP TABLE IF EXISTS holding'))
        conn.commit()
    
    print("Recreating tables...")
    SQLModel.metadata.create_all(engine)
    
    print("Re-calculating holdings from transactions...")
    with Session(engine) as session:
        update_holdings(session)
    
    print("Sync completed.")

if __name__ == "__main__":
    reset_and_sync()

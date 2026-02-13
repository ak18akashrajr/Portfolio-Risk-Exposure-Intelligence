import os
from sqlmodel import create_engine, SQLModel, Session

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "portfolio_v2.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def create_db_and_tables():
    from .models import Transaction, Holding
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

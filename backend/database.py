from sqlmodel import create_engine, SQLModel, Session
import os

DATABASE_URL = "sqlite:///./portfolio_v2.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def create_db_and_tables():
    from .models import Transaction, Holding
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

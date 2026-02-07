from sqlmodel import Session, select
from app.models import User, Portfolio, Asset, Transaction
from app.schemas import UserCreate, PortfolioCreate, AssetBase
from uuid import UUID

def create_user(session: Session, user: UserCreate) -> User:
    db_user = User.from_orm(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()

def create_portfolio(session: Session, portfolio: PortfolioCreate) -> Portfolio:
    db_portfolio = Portfolio.from_orm(portfolio)
    session.add(db_portfolio)
    session.commit()
    session.refresh(db_portfolio)
    return db_portfolio

def get_portfolios_by_user(session: Session, user_id: UUID) -> list[Portfolio]:
    statement = select(Portfolio).where(Portfolio.user_id == user_id)
    return session.exec(statement).all()

def get_portfolio(session: Session, portfolio_id: UUID) -> Portfolio | None:
    return session.get(Portfolio, portfolio_id)

def get_asset_by_symbol(session: Session, symbol: str) -> Asset | None:
    statement = select(Asset).where(Asset.symbol == symbol)
    return session.exec(statement).first()

def create_asset(session: Session, asset: AssetBase) -> Asset:
    db_asset = Asset.from_orm(asset)
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
    return db_asset

def create_transaction(session: Session, transaction: Transaction) -> Transaction:
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

def get_transactions_by_portfolio(session: Session, portfolio_id: UUID) -> list[Transaction]:
    statement = select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    return session.exec(statement).all()

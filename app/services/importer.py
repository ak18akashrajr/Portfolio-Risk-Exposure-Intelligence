from sqlmodel import Session, select
from app.models import Portfolio, User
# All file import logic removed. 
# This file is now deprecated or minimal.

def ingest_folder(session: Session, folder_path: str = "holdings_transactions"):
    """
    DEPRECATED: Now only ensures default portfolio exists.
    Previous functionality of reading Excel files is REMOVED.
    """
    # 1. Setup Default Context
    user = session.exec(select(User).where(User.email == "default@user.com")).first()
    if not user:
        user = User(name="Default User", email="default@user.com")
        session.add(user)
        session.commit()
    
    portfolio = session.exec(select(Portfolio).where(Portfolio.user_id == user.id)).first()
    if not portfolio:
        portfolio = Portfolio(name="Main Portfolio", user_id=user.id, base_currency="INR")
        session.add(portfolio)
        session.commit()
        
    return portfolio.id

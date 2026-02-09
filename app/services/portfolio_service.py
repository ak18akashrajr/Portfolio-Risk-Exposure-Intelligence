from sqlmodel import Session, select
from app.models import Portfolio, User, Asset, Transaction, Holding
from app.schemas import TransactionCreate
from app.services.yfinance_service import get_ticker_symbol, get_asset_info
from datetime import datetime

def ensure_default_user_and_portfolio(session: Session) -> Portfolio:
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
        session.refresh(portfolio)
        
    return portfolio

def clear_all_data(session: Session, portfolio_id: object):
    """Clears all transactions and holdings for a portfolio"""
    # Delete Transactions
    transactions = session.exec(select(Transaction).where(Transaction.portfolio_id == portfolio_id)).all()
    for t in transactions:
        session.delete(t)
        
    # Delete Holdings
    holdings = session.exec(select(Holding).where(Holding.portfolio_id == portfolio_id)).all()
    for h in holdings:
        session.delete(h)
        
    session.commit()

def ensure_asset(session: Session, symbol: str) -> Asset:
    """Ensures asset exists in DB, fetching info from YFinance if needed"""
    # Standardize symbol
    symbol = symbol.strip().upper()
    
    # Try finding exact match
    asset = session.exec(select(Asset).where(Asset.symbol == symbol)).first()
    
    if not asset:
        # Fetch Info
        yf_sym = get_ticker_symbol(symbol)
        info = get_asset_info(yf_sym)
        
        # If not found with .NS, try without suffix? 
        # (Asset info logic handles it, but let's trust get_asset_info's return)
        
        sector = info.get("sector")
        mcap = info.get("market_cap_bucket")
        currency = info.get("currency", "INR")
        
        # If YFinance failed to give price, it might be invalid, but we create it anyway?
        # User explicitly adding it, so we trust them or we assume it's valid.
        
        asset = Asset(
            symbol=symbol, # Store as entered/standardized
            exchange="NSE", # Default
            asset_type="Equity", # Default to Equity for now
            sector=sector,
            market_cap_bucket=mcap,
            currency=currency
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        
    return asset

def add_transaction_direct(session: Session, txn: TransactionCreate) -> str:
    """
    Adds a transaction and updates the Holding record (Weighted Average).
    """
    portfolio = ensure_default_user_and_portfolio(session)
    
    # 1. Ensure Asset
    asset = ensure_asset(session, txn.symbol)
    
    # 2. Add Transaction
    transaction = Transaction(
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        transaction_date=txn.transaction_date,
        quantity=txn.quantity,
        price=txn.price,
        transaction_type=txn.transaction_type.upper()
    )
    session.add(transaction)
    
    # 3. Update Holding
    holding = session.exec(select(Holding).where(
        Holding.portfolio_id == portfolio.id,
        Holding.asset_id == asset.id
    )).first()
    
    qty = txn.quantity
    price = txn.price
    txn_type = txn.transaction_type.upper()
    
    if not holding:
        if txn_type == "BUY":
            holding = Holding(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                quantity=qty,
                avg_cost=price,
                market_value=qty * price, # Init value
                snapshot_date=datetime.now().date()
            )
            session.add(holding)
        # If SELL and no holding, we can't sell? Allow for now (short selling?) 
        # or just ignore. Let's assume BUY first.
    else:
        current_qty = holding.quantity
        current_cost = holding.avg_cost
        
        if txn_type == "BUY":
            # Weighted Avg Logic
            new_total_qty = current_qty + qty
            new_avg_cost = ((current_qty * current_cost) + (qty * price)) / new_total_qty if new_total_qty > 0 else 0
            
            holding.quantity = new_total_qty
            holding.avg_cost = new_avg_cost
            # Market Value will be updated by Dashboard live fetch, 
            # but here we can update it based on txn price as a proxy?
            holding.market_value = new_total_qty * price 
            
        elif txn_type == "SELL":
            # FIFO/Avg Cost
            # Realized P&L is not tracked in Holding, only remaining Qty
            new_qty = max(0, current_qty - qty)
            holding.quantity = new_qty
            # Avg Cost remains same for SELL (Indian Accounting usually)
            
            holding.market_value = new_qty * price # Proxy
            
            if new_qty == 0:
                # Optional: Delete holding or keep with 0?
                # Keep with 0 to show in history if needed? 
                # Or delete to remove from dashboard.
                # Let's keep with 0.
                pass
                
        session.add(holding)
        
    session.commit()
    return "Transaction Added"

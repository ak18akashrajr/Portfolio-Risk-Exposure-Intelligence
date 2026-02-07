import pandas as pd
import os
from sqlmodel import Session, select
from app.models import Portfolio, Transaction, Asset, User
from app.services.yfinance_service import get_ticker_symbol, get_asset_info
from datetime import datetime
import glob

def find_header_row(df: pd.DataFrame, keywords: list[str]) -> int:
    """Scan first 30 rows for keywords to identify header"""
    for i, row in df.head(30).iterrows():
        row_str = " ".join(row.astype(str)).lower()
        if all(k in row_str for k in keywords):
            return i
    return -1

def ingest_folder(session: Session, folder_path: str = "holdings_transactions"):
    # 1. Setup Default Context
    # Find or Create Default User
    user = session.exec(select(User).where(User.email == "default@user.com")).first()
    if not user:
        user = User(name="Default User", email="default@user.com")
        session.add(user)
        session.commit()
    
    # Find or Create Default Portfolio
    portfolio = session.exec(select(Portfolio).where(Portfolio.user_id == user.id)).first()
    if not portfolio:
        portfolio = Portfolio(name="Main Portfolio", user_id=user.id, base_currency="INR")
        session.add(portfolio)
        session.commit()
    
    # Clear existing transactions/holdings for fresh ingest
    # (Cascading delete would be better, but doing manually for safety)
    existing_txs = session.exec(select(Transaction).where(Transaction.portfolio_id == portfolio.id)).all()
    for tx in existing_txs:
        session.delete(tx)
    session.commit()
    
    # 2. Process Files
    files = glob.glob(os.path.join(folder_path, "*.xlsx"))
    
    for file_path in files:
        filename = os.path.basename(file_path).lower()
        
        try:
            if "stocks_order" in filename:
                _process_stock_orders(session, portfolio.id, file_path)
            elif "mutual_funds_order" in filename:
                _process_mf_orders(session, portfolio.id, file_path)
            # Add handling for Holdings files if needed for verification later
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    return portfolio.id

def _process_stock_orders(session: Session, portfolio_id: object, file_path: str):
    # Load raw
    df = pd.read_excel(file_path, header=None)
    
    # Find header
    header_idx = find_header_row(df, ["symbol", "quantity", "type"])
    if header_idx == -1:
        print(f"Skipping {file_path}: Header not found")
        return
        
    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    
    # Normalize columns
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # Expected cols: symbol, type, quantity, execution date and time, price/value? 
    # From inspection: 'Stock name', 'Symbol', 'ISIN', 'Type', 'Quantity', 'Value', 'Exchange', ... 'Order status'
    # Need Price. Value provided? Or derive?
    
    for _, row in df.iterrows():
        status = str(row.get('order status', '')).lower()
        if status != 'executed':
            continue
            
        symbol = row['symbol']
        txn_type = row['type'] # BUY/SELL
        qty = float(row['quantity'])
        # Value is total value?
        try:
            val = float(row.get('value', 0) or row.get('amount', 0)) # handle variations
            price = val / qty if qty > 0 and val > 0 else 0
        except:
            price = 0
            
        date_str = str(row.get('execution date and time', ''))
        # Format: 29-08-2022 09:57 AM
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y %I:%M %p").date()
        except:
             try:
                 dt = datetime.strptime(date_str, "%d-%m-%Y").date()
             except:
                 dt = datetime.now().date()
        
        # Ensure Asset
        yf_symbol = get_ticker_symbol(symbol)
        asset = session.exec(select(Asset).where(Asset.symbol == yf_symbol)).first()
        if not asset:
            info = get_asset_info(yf_symbol)
            asset = Asset(
                symbol=yf_symbol,
                exchange="NSE",
                asset_type="Equity",
                sector=info.get("sector"),
                market_cap_bucket=info.get("market_cap_bucket"),
                currency="INR"
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            
        # Create Transaction
        tx = Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            transaction_date=dt,
            quantity=qty,
            price=price,
            transaction_type=txn_type.upper()
        )
        session.add(tx)
    session.commit()

def _process_mf_orders(session: Session, portfolio_id: object, file_path: str):
    df = pd.read_excel(file_path, header=None)
    header_idx = find_header_row(df, ["scheme name", "units", "amount"])
    if header_idx == -1:
        return

    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    # Cols: Scheme Name, Transaction Type, Units, NAV, Amount, Date
    
    for _, row in df.iterrows():
        scheme = row.get('scheme name')
        if not scheme or pd.isna(scheme): continue
        
        t_type = str(row.get('transaction type', '')).lower() # purchase / redeem
        if 'purchase' in t_type or 'sip' in t_type:
            txn_type = "BUY"
        elif 'redeem' in t_type or 'sell' in t_type:
            txn_type = "SELL"
        else:
            print(f"Unknown MF type: {t_type}")
            continue
            
        qty = float(row['units'])
        price = float(row.get('nav', 0))
        
        date_str = str(row.get('date', ''))
        # Format: 19 Jan 2026
        try:
            dt = datetime.strptime(date_str, "%d %b %Y").date()
        except:
            dt = datetime.now().date()
            
        # Asset (MF) - Skip YFinance for now as symbols are hard
        asset_sym = scheme[:28].upper().replace(" ", "_") # Temporary Symbol
        asset = session.exec(select(Asset).where(Asset.symbol == asset_sym)).first()
        if not asset:
            asset = Asset(
                symbol=asset_sym,
                exchange="MF",
                asset_type="Mutual Fund",
                sector="Financial Services", # Generic
                market_cap_bucket=None,
                currency="INR"
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            
        tx = Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            transaction_date=dt,
            quantity=qty,
            price=price,
            transaction_type=txn_type
        )
        session.add(tx)
    session.commit()

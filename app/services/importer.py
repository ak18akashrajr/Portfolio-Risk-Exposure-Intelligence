import pandas as pd
import os
import glob
from sqlmodel import Session, select
from app.models import Portfolio, Transaction, Asset, User, Holding
from app.services.yfinance_service import get_ticker_symbol, get_asset_info
from datetime import datetime

def find_header_row(df: pd.DataFrame, keywords: list[str]) -> int:
    """Scan first 30 rows for keywords to identify header"""
    for i, row in df.head(30).iterrows():
        row_str = " ".join(row.astype(str)).lower()
        if all(k in row_str for k in keywords):
            return i
    return -1

def ingest_folder(session: Session, folder_path: str = "holdings_transactions"):
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
    
    # Clear existing data
    session.exec(select(Transaction).where(Transaction.portfolio_id == portfolio.id))
    for tx in session.exec(select(Transaction).where(Transaction.portfolio_id == portfolio.id)).all():
        session.delete(tx)
    
    for h in session.exec(select(Holding).where(Holding.portfolio_id == portfolio.id)).all():
        session.delete(h)
    
    session.commit()
    
    # 2. Process Files
    files = glob.glob(os.path.join(folder_path, "*.xlsx"))
    
    for file_path in files:
        filename = os.path.basename(file_path).lower()
        print(f"Processing {filename}...")
        
        try:
            # HISTORY
            if "stocks_order_history" in filename:
                _process_stock_history(session, portfolio.id, file_path)
            elif "mutual_funds_order_history" in filename:
                _process_mf_history(session, portfolio.id, file_path)
            
            # HOLDINGS
            elif "stocks_holdings_statement" in filename:
                _process_stock_holdings(session, portfolio.id, file_path)
            elif "mutual_funds_" in filename and "order_history" not in filename: 
                # "Mutual_Funds_1551826140_...xlsx"
                _process_mf_holdings(session, portfolio.id, file_path)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    return portfolio.id

# --- HISTORY PROCESSORS ---

def _process_stock_history(session: Session, portfolio_id: object, file_path: str):
    df = pd.read_excel(file_path, header=None)
    header_idx = find_header_row(df, ["symbol", "quantity", "type"])
    if header_idx == -1: return

    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    for _, row in df.iterrows():
        status = str(row.get('order status', '')).lower()
        if status != 'executed': continue
            
        symbol = str(row['symbol'])
        txn_type = str(row['type'])
        qty = float(row['quantity'])
        try:
            val = float(row.get('value', 0) or row.get('amount', 0))
            price = val / qty if qty > 0 and val > 0 else 0
        except: price = 0
            
        date_str = str(row.get('execution date and time', ''))
        try: dt = datetime.strptime(date_str, "%d-%m-%Y %I:%M %p").date()
        except: 
            try: dt = datetime.strptime(date_str, "%d-%m-%Y").date()
            except: dt = datetime.now().date()
        
        asset = _ensure_asset(session, symbol, "Equity")
        
        tx = Transaction(
            portfolio_id=portfolio_id, asset_id=asset.id, transaction_date=dt,
            quantity=qty, price=price, transaction_type=txn_type.upper()
        )
        session.add(tx)
    session.commit()

def _process_mf_history(session: Session, portfolio_id: object, file_path: str):
    df = pd.read_excel(file_path, header=None)
    header_idx = find_header_row(df, ["scheme name", "units", "amount"])
    if header_idx == -1: return

    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    for _, row in df.iterrows():
        scheme = row.get('scheme name')
        if not scheme or pd.isna(scheme): continue
        
        t_type = str(row.get('transaction type', '')).lower()
        if 'purchase' in t_type or 'sip' in t_type: txn_type = "BUY"
        elif 'redeem' in t_type or 'sell' in t_type: txn_type = "SELL"
        else: continue
            
        qty = float(row['units'])
        price = float(row.get('nav', 0))
        date_str = str(row.get('date', ''))
        try: dt = datetime.strptime(date_str, "%d %b %Y").date()
        except: dt = datetime.now().date()
            
        asset = _ensure_asset(session, scheme, "Mutual Fund") # Use scheme name as symbol key for MFs
        
        tx = Transaction(
            portfolio_id=portfolio_id, asset_id=asset.id, transaction_date=dt,
            quantity=qty, price=price, transaction_type=txn_type
        )
        session.add(tx)
    session.commit()

# --- HOLDINGS PROCESSORS ---

def _process_stock_holdings(session: Session, portfolio_id: object, file_path: str):
    # Header: Stock Name, ISIN, Quantity, Average buy price, Buy value, ...
    df = pd.read_excel(file_path, header=None)
    header_idx = find_header_row(df, ["stock name", "isin", "quantity"])
    if header_idx == -1: return
    
    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    df.columns = [str(c).lower().strip() for c in df.columns]

    for _, row in df.iterrows():
        # Clean up column names mappings
        stock_name = row.get('stock name')
        isin = row.get('isin')
        if not isin or pd.isna(isin): continue
        
        # Try to find symbol from ISIN or name? 
        # Usually Groww Stocks Holdings doesn't have Ticker Symbol explicitly sometimes?
        # Sample: Stock Name, ISIN, Quantity... 
        # But we need Ticker for Yahoo Finance.
        # Importer Logic: We'll try to guess/map or use what we have.
        # Actually in the previous task, I saw: 
        # "MOTILAL OS NASDAQ100 ETF", "INF247L01AP3"
        # "NIP IND ETF BANK BEES", "INF204KB15I9"
        # We need a mapper. For now, let's use ISIN as symbol if we can't find better, 
        # BUT wait, the History file has 'symbol'. 
        
        # Strategy: 
        # 1. Check if we already created an Asset with this ISIN (unlikely)
        # 2. Try to map Name to Symbol (Risky)
        # 3. For now, let's look for a Symbol column if it exists. 
        # If not, we might be in trouble for Live Prices.
        # Let's check the sample again... 
        # "Stock Name", "ISIN", "Quantity".
        # Stocks_Order_History has "Symbol".
        # We can link via Name if exact match?
        
        # Let's just create Asset with ISIN as fallback symbol, 
        # AND try to match with existing Assets (created by history ingest) by Name?
        # No, let's use ISIN as the unique key if possible?
        
        # BETTER: The Order History runs FIRST in the loop above? 
        # No, glob order is random.
        # Let's ensure we can link them.
        
        qty = float(row['quantity'])
        avg_price = float(row.get('average buy price', 0))
        
        # Use ISIN as symbol if we can't find a better one from YFinance lookup 
        # (which is hard with just ISIN)
        
        # Optimization: We'll assume the user put Order History file too.
        # If we see this Name in DB (from Order History), reuse that Asset.
        
        # For now, let's use the Stock Name to search YFinance if needed?
        # Or just use the Name as Symbol for Internal ref.
        
        market_val = float(row.get('closing value', 0) or 0)
        
        # Store
        # For Stocks, we REALLY want the Ticker.
        # Let's assume we can find it or we just store Name.
        asset_symbol = isin # Fallback
        
        # Try to fuzzy match with assets created from History?
        # History has "PNB", Name "PUNJAB NATIONAL BANK"
        # Holding has Name "PUNJAB NATIONAL BANK"
        
        # We will try to find Asset by Name first (if we stored Name in Asset? We didn't, we stored Symbol)
        # Okay, let's just create a new Asset if needed, but this might duplicate.
        
        asset = _ensure_asset(session, stock_name, "Equity") # Use Name as Symbol for now if unknown
        # _ensure_asset will check by Symbol. If we pass Name as Symbol, it checks that.
        
        h = Holding(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            quantity=qty,
            avg_cost=avg_price,
            market_value=market_val, # From file (Snapshot)
            snapshot_date=datetime.now().date()
        )
        session.add(h)
    session.commit()

def _process_mf_holdings(session: Session, portfolio_id: object, file_path: str):
    # Header: Scheme Name, ..., Units, Invested Value, Current Value, ...
    df = pd.read_excel(file_path, header=None)
    header_idx = find_header_row(df, ["scheme name", "units", "invested value"])
    if header_idx == -1: return

    df.columns = df.iloc[header_idx]
    df = df.iloc[header_idx+1:].reset_index(drop=True)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    for _, row in df.iterrows():
        scheme = row.get('scheme name')
        if not scheme or pd.isna(scheme): continue
        
        units = float(row['units'])
        inv_val = float(row['invested value'])
        curr_val = float(row['current value'])
        
        avg_cost = inv_val / units if units > 0 else 0
        
        asset = _ensure_asset(session, scheme, "Mutual Fund")
        
        h = Holding(
            portfolio_id=portfolio_id,
            asset_id=asset.id,
            quantity=units,
            avg_cost=avg_cost,
            market_value=curr_val,
            snapshot_date=datetime.now().date()
        )
        session.add(h)
    session.commit()

def _ensure_asset(session: Session, identifier: str, asset_type: str) -> Asset:
    """
    Finds or Creates asset. 
    'identifier' can be Ticker (Equity) or Scheme Name (MF).
    """
    # Simple lookup
    # Clean identifier
    identifier = identifier.strip().upper() if identifier else "UNKNOWN"
    
    # Try finding exact match
    asset = session.exec(select(Asset).where(Asset.symbol == identifier)).first()
    
    if not asset:
        # If Equity, try to get info from YFinance using identifier as Ticker
        sector = None
        mcap = None
        
        if asset_type == "Equity":
            yf_sym = get_ticker_symbol(identifier) # Adds .NS
            info = get_asset_info(yf_sym) # Allows checking if valid
            # If info is good, use yf_sym as symbol. 
            # If not (e.g. identifier is "PUNJAB NATIONAL BANK"), this fails.
            
            # If valid ticker
            if info.get("current_price", 0) > 0:
                identifier = yf_sym # Update to canonical ticker
                sector = info.get("sector")
                mcap = info.get("market_cap_bucket")
            else:
                # Identifier is likely a Name. 
                # We can't easily get Sector/Price for "PUNJAB NATIONAL BANK" without search API.
                # Keep Name as Symbol for now.
                pass
                
        asset = Asset(
            symbol=identifier,
            exchange="NSE" if asset_type == "Equity" else "MF",
            asset_type=asset_type,
            sector=sector,
            market_cap_bucket=mcap,
            currency="INR"
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        
    return asset

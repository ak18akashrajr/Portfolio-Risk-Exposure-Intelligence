import pandas as pd
from datetime import datetime
from sqlmodel import Session, select
from .models import Transaction, Holding
from .database import engine
from typing import List, Dict, Optional, Tuple

# Mapping for Mutual Fund Scheme Names to Yahoo Finance Tickers
MF_TICKER_MAP = {
    "Parag Parikh Flexi Cap Fund Direct Growth": "0P0000YWL1.BO",
    # Add more mappings here as needed
}

def ingest_excel(file_path: str):
    # Peek at the file to determine type
    peek_df = pd.read_excel(file_path, nrows=20)
    is_mf_holdings = any(peek_df.iloc[:, 0].astype(str).str.contains("HOLDING SUMMARY|HOLDINGS AS ON", na=False))
    is_mf_orders = any(peek_df.iloc[:, 0].astype(str).str.contains("TRANSACTIONS FROM", na=False))
    
    if is_mf_holdings or is_mf_orders:
        ingest_mutual_funds(file_path, is_orders=is_mf_orders)
        return

    # Header is at row 5 (0-indexed) for Stocks
    df = pd.read_excel(file_path, header=5)
    
    # Rename columns to match model
    column_mapping = {
        'Stock name': 'stock_name',
        'Symbol': 'symbol',
        'ISIN': 'isin',
        'Type': 'type',
        'Quantity': 'quantity',
        'Value': 'price',
        'Exchange': 'exchange',
        'Exchange Order Id': 'order_id',
        'Execution date and time': 'execution_time',
        'Order status': 'status'
    }
    df = df.rename(columns=column_mapping)
    
    # Filter only 'Executed' orders
    df = df[df['status'] == 'Executed']
    
    # Convert execution_time to datetime
    df['execution_time'] = pd.to_datetime(df['execution_time'], format='%d-%m-%Y %I:%M %p')
    
    with Session(engine) as session:
        for _, row in df.iterrows():
            # Check if transaction already exists
            existing = session.exec(select(Transaction).where(Transaction.order_id == str(row['order_id']))).first()
            if not existing:
                transaction = Transaction(
                    stock_name=row['stock_name'],
                    symbol=row['symbol'],
                    isin=row['isin'],
                    type=row['type'],
                    quantity=row['quantity'],
                    price=row['price'],
                    exchange=row['exchange'],
                    order_id=str(row['order_id']),
                    execution_time=row['execution_time'],
                    geography="India",
                    category="Commodity" if str(row['symbol']).upper() == "GOLDBEES" else "Equity(Stocks)",
                    status=row['status']
                )
                session.add(transaction)
        
        session.commit()
        update_holdings(session)

def ingest_mutual_funds(file_path: str, is_orders: bool):
    # Find header row dynamically
    df_raw = pd.read_excel(file_path, header=None, nrows=30)
    header_row = -1
    target_keyword = "Scheme Name"
    for i, row in df_raw.iterrows():
        if any(target_keyword in str(val) for val in row if pd.notna(val)):
            header_row = i
            break
    
    if header_row == -1:
        # Fallback to defaults if not found
        header_row = 10 if is_orders else 19
        
    df = pd.read_excel(file_path, header=header_row)
    
    # Clean numeric columns (handle commas and strings)
    def clean_numeric(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            val = val.replace(',', '').strip()
            if not val or val == '-': return 0.0
            try:
                return float(val)
            except:
                return 0.0
        return 0.0

    mf_prices_from_file = {}

    if is_orders:
        # Normalize Order History
        df.columns = [str(c).strip() for c in df.columns]
        
        col_map = {
            'Scheme Name': 'stock_name',
            'Type': 'type',
            'Units': 'quantity',
            'NAV': 'price',
            'Amount': 'total_value',
            'Date': 'execution_time'
        }
        
        df = df.rename(columns={c: col_map[c] for c in df.columns if c in col_map})
        
        if 'stock_name' not in df.columns and 'Unnamed: 0' in df.columns:
            df = df.rename(columns={
                'Unnamed: 0': 'stock_name',
                'Unnamed: 1': 'type',
                'Unnamed: 2': 'quantity',
                'Unnamed: 3': 'price',
                'Unnamed: 4': 'total_value',
                'Unnamed: 5': 'execution_time'
            })
            
        df = df[df['stock_name'].notna() & (df['stock_name'].astype(str).str.contains("Scheme Name") == False)]
        df['stock_name'] = df['stock_name'].astype(str).str.strip()
        df['quantity'] = df['quantity'].apply(clean_numeric)
        df['price'] = df['price'].apply(clean_numeric)
        if 'total_value' in df.columns:
            df['total_value'] = df['total_value'].apply(clean_numeric)
        
        if 'type' in df.columns:
            df['type'] = df['type'].astype(str).str.upper().map({'PURCHASE': 'BUY', 'REDEMPTION': 'SELL'}).fillna('BUY')
        else:
            df['type'] = 'BUY'
            
        df['execution_time'] = pd.to_datetime(df['execution_time'], errors='coerce')
        df = df[df['execution_time'].notna()]
        
        df['status'] = 'Executed'
        df['exchange'] = 'MUTUAL_FUND'
        
        # Use ticker mapping if available, otherwise fallback to scheme name
        df['symbol'] = df['stock_name'].map(MF_TICKER_MAP).fillna(df['stock_name'])
        df['isin'] = 'MF_ISIN'
        df['folio_number'] = 'MF_FOLIO'
        
        with Session(engine) as session:
            for _, row in df.iterrows():
                pseudo_id = f"MF_{row['execution_time'].strftime('%Y%m%d')}_{row['stock_name']}"
                existing = session.exec(select(Transaction).where(Transaction.order_id == pseudo_id)).first()
                if not existing:
                    transaction = Transaction(
                        stock_name=row['stock_name'],
                        symbol=row['symbol'],
                        isin=row['isin'],
                        type=row['type'],
                        quantity=row['quantity'],
                        price=row['total_value'], # Use total amount here
                        exchange=row['exchange'],
                        order_id=pseudo_id,
                        execution_time=row['execution_time'],
                        geography="India",
                        category="Mutual Fund",
                        folio_number=row['folio_number'],
                        status=row['status']
                    )
                    session.add(transaction)
            session.commit()
            update_holdings(session)
    else:
        # Normalize Holdings
        df.columns = [str(c).strip() for c in df.columns]
        scheme_col = next((c for c in df.columns if 'Scheme' in c), 'Scheme Name')
        folio_col = next((c for c in df.columns if 'Folio' in c), None)
        units_col = next((c for c in df.columns if 'Units' in c), None)
        value_col = next((c for c in df.columns if 'Invested' in c), None)
        cur_val_col = next((c for c in df.columns if 'Current Value' in c), None)
        
        df = df[df[scheme_col].notna() & (df[scheme_col].astype(str).str.contains("Scheme Name") == False)]
        
        with Session(engine) as session:
            for _, row in df.iterrows():
                scheme = str(row[scheme_col]).strip()
                folio = str(row[folio_col]).strip() if folio_col and pd.notna(row[folio_col]) else "MF_FOLIO"
                
                # Extract pricing info for persistence
                units = clean_numeric(row[units_col]) if units_col else 0.0
                current_valuation = clean_numeric(row[cur_val_col]) if cur_val_col else 0.0
                current_price = current_valuation / units if units > 0 else None
                if current_price:
                    mf_prices_from_file[(scheme, folio)] = current_price
                
                # 1. Update existing "MF_FOLIO" transactions for this scheme with the real folio
                if folio != "MF_FOLIO":
                    existing_placeholders = session.exec(
                        select(Transaction).where(Transaction.symbol == scheme, Transaction.folio_number == "MF_FOLIO")
                    ).all()
                    for tx in existing_placeholders:
                        tx.folio_number = folio
                        session.add(tx)
                    session.flush() 
                
                # 2. Check if we already have transactions for this scheme to avoid double counting
                has_tx = session.exec(
                    select(Transaction).where(Transaction.symbol == scheme, Transaction.folio_number == folio)
                ).first()
                
                if not has_tx:
                    pseudo_id = f"MF_HOLDING_{folio}_{scheme}"
                    invested = clean_numeric(row[value_col]) if value_col else 0.0
                    
                    # Use ticker mapping
                    ticker = MF_TICKER_MAP.get(scheme, scheme)
                    
                    transaction = Transaction(
                        stock_name=scheme,
                        symbol=ticker,
                        isin="MF_ISIN",
                        type="BUY",
                        quantity=units,
                        price=invested, # Total invested value
                        exchange='MUTUAL_FUND',
                        order_id=pseudo_id,
                        execution_time=datetime.now().replace(microsecond=0),
                        geography="India",
                        category="Mutual Fund",
                        folio_number=folio,
                        status="Executed"
                    )
                    session.add(transaction)
                    session.flush()
            session.commit()
            update_holdings(session, mf_prices=mf_prices_from_file)

def update_holdings(session: Session, mf_prices: Dict[Tuple[str, str], float] = None):
    transactions = session.exec(select(Transaction)).all()
    holdings_dict = {}
    
    for tx in transactions:
        key = (tx.symbol, tx.folio_number)
        if key not in holdings_dict:
            holdings_dict[key] = {
                'symbol': tx.symbol,
                'stock_name': tx.stock_name,
                'isin': tx.isin,
                'current_quantity': 0.0,
                'total_invested': 0.0,
                'geography': tx.geography,
                'category': tx.category,
                'folio_number': tx.folio_number,
                'last_transaction_date': tx.execution_time
            }
        
        if tx.type.upper() == 'BUY':
            holdings_dict[key]['current_quantity'] += tx.quantity
            holdings_dict[key]['total_invested'] += tx.price 
        else:
            if holdings_dict[key]['current_quantity'] > 0:
                reduction_ratio = tx.quantity / holdings_dict[key]['current_quantity']
                holdings_dict[key]['total_invested'] *= (1 - reduction_ratio)
            holdings_dict[key]['current_quantity'] -= tx.quantity
            
        if tx.execution_time > holdings_dict[key]['last_transaction_date']:
            holdings_dict[key]['last_transaction_date'] = tx.execution_time

    existing_holdings = session.exec(select(Holding)).all()
    existing_keys = {(h.symbol, h.folio_number): h for h in existing_holdings}
    calculated_keys = set(holdings_dict.keys())

    # Update or Add holdings
    for key, data in holdings_dict.items():
        if data['current_quantity'] <= 0:
            if key in existing_keys:
                session.delete(existing_keys[key])
            continue

        if key in existing_keys:
            holding = existing_keys[key]
            holding.quantity = data['current_quantity']
            holding.total_invested = data['total_invested']
            holding.avg_price = data['total_invested'] / data['current_quantity'] if data['current_quantity'] > 0 else 0
            holding.last_transaction_date = data['last_transaction_date']
            holding.stock_name = data['stock_name']
            holding.isin = data['isin']
            holding.geography = data['geography']
            holding.category = data['category']
        else:
            holding = Holding(
                symbol=data['symbol'],
                stock_name=data['stock_name'],
                isin=data['isin'],
                quantity=data['current_quantity'],
                avg_price=data['total_invested'] / data['current_quantity'] if data['current_quantity'] > 0 else 0,
                total_invested=data['total_invested'],
                geography=data['geography'],
                category=data['category'],
                folio_number=data['folio_number'],
                last_transaction_date=data['last_transaction_date'],
                last_updated_at=datetime.now()
            )
            session.add(holding)

        # Apply MF prices from file if provided
        if mf_prices and key in mf_prices:
            holding.current_price = mf_prices[key]
            holding.current_valuation = holding.current_price * holding.quantity
            holding.last_updated_at = datetime.now()
            
    # Cleanup: Delete holdings no longer in transactions
    for key in (set(existing_keys.keys()) - calculated_keys):
        session.delete(existing_keys[key])
            
    session.commit()

import random

def add_manual_transaction(session: Session, symbol: str, tx_type: str, quantity: float, price: float, exchange: str, stock_name: str = None, isin: str = None, geography: str = "India", category: str = "Equity(Stocks)", folio_number: str = None):
    # Reverse map for ticker to name lookup if needed, or vice-versa
    if category == "Mutual Fund":
        # If symbol is a name in the map, replace with ticker
        if symbol in MF_TICKER_MAP:
            stock_name = stock_name or symbol
            symbol = MF_TICKER_MAP[symbol]
        # If symbol is already a ticker but name is missing, try to find name
        elif not stock_name:
            for name, ticker in MF_TICKER_MAP.items():
                if ticker == symbol:
                    stock_name = name
                    break

    # Auto-fetch metadata from existing holdings if not provided
    if not stock_name or not isin:
        # Try finding by symbol first
        query = select(Holding).where(Holding.symbol == symbol)
        if folio_number:
            query = query.where(Holding.folio_number == folio_number)
        existing_holding = session.exec(query).first()
        
        # If not found by symbol, and it's a Mutual Fund, try finding by name if symbol was the name
        if not existing_holding and category == "Mutual Fund" and stock_name:
            query = select(Holding).where(Holding.stock_name == stock_name)
            if folio_number:
                query = query.where(Holding.folio_number == folio_number)
            existing_holding = session.exec(query).first()

        if existing_holding:
            stock_name = stock_name or existing_holding.stock_name
            isin = isin or existing_holding.isin
            geography = geography or existing_holding.geography
            category = category or existing_holding.category
            folio_number = folio_number or existing_holding.folio_number
    
    order_id = f"{random.randint(1000000000000000, 9999999999999999)}.0"
    
    transaction = Transaction(
        stock_name=stock_name or symbol,
        symbol=symbol,
        isin=isin or "MANUAL",
        type=tx_type,
        quantity=quantity,
        price=price,
        exchange=exchange,
        order_id=order_id,
        execution_time=datetime.now().replace(microsecond=0),
        geography=geography or "India",
        category=category or "Equity(Stocks)",
        folio_number=folio_number,
        status="Executed"
    )
    
    session.add(transaction)
    session.commit()
    update_holdings(session)
    return transaction

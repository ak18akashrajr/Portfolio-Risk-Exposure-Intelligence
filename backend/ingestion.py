import pandas as pd
from datetime import datetime
from sqlmodel import Session, select
from .models import Transaction, Holding
from .database import engine

def ingest_excel(file_path: str):
    # Header is at row 5 (0-indexed)
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
                    status=row['status']
                )
                session.add(transaction)
        
        session.commit()
        update_holdings(session)

def update_holdings(session: Session):
    # Recalculate holdings based on transactions
    transactions = session.exec(select(Transaction)).all()
    holdings_dict = {}
    
    for tx in transactions:
        if tx.symbol not in holdings_dict:
            holdings_dict[tx.symbol] = {
                'stock_name': tx.stock_name,
                'isin': tx.isin,
                'current_quantity': 0,
                'total_buy_quantity': 0,
                'total_buy_value': 0.0,
                'last_transaction_date': tx.execution_time
            }
        
        # Update last transaction date
        if tx.execution_time > holdings_dict[tx.symbol]['last_transaction_date']:
            holdings_dict[tx.symbol]['last_transaction_date'] = tx.execution_time

        if tx.type.upper() == 'BUY':
            holdings_dict[tx.symbol]['current_quantity'] += tx.quantity
            holdings_dict[tx.symbol]['total_buy_quantity'] += tx.quantity
            holdings_dict[tx.symbol]['total_buy_value'] += tx.price # tx.price is 'Value' column
        elif tx.type.upper() == 'SELL':
            holdings_dict[tx.symbol]['current_quantity'] -= tx.quantity
            if holdings_dict[tx.symbol]['current_quantity'] < 0:
                holdings_dict[tx.symbol]['current_quantity'] = 0

    # Overwrite holdings in DB
    for symbol, data in holdings_dict.items():
        if data['current_quantity'] > 0:
            # Weighted Average Buy Price = Total Buy Value / Total Buy Quantity
            avg_price = data['total_buy_value'] / data['total_buy_quantity'] if data['total_buy_quantity'] > 0 else 0
            
            holding = session.get(Holding, symbol)
            if holding:
                holding.quantity = data['current_quantity']
                holding.avg_price = avg_price
                holding.total_invested = data['current_quantity'] * avg_price # Current value at cost
                holding.isin = data['isin']
                holding.last_transaction_date = data['last_transaction_date']
            else:
                holding = Holding(
                    symbol=symbol,
                    stock_name=data['stock_name'],
                    isin=data['isin'],
                    quantity=data['current_quantity'],
                    avg_price=avg_price,
                    total_invested=data['current_quantity'] * avg_price,
                    last_transaction_date=data['last_transaction_date']
                )
            session.add(holding)
    
    session.commit()

import random

def add_manual_transaction(session: Session, symbol: str, tx_type: str, quantity: int, price: float, exchange: str, stock_name: str = None, isin: str = None):
    # Auto-fetch metadata from existing holdings if not provided
    if not stock_name or not isin:
        existing_holding = session.get(Holding, symbol)
        if existing_holding:
            stock_name = stock_name or existing_holding.stock_name
            isin = isin or existing_holding.isin
    
    # Generate random order_id in format 1200000004627407.0
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
        execution_time=datetime.now(),
        status="Executed"
    )
    
    session.add(transaction)
    session.commit()
    update_holdings(session)
    return transaction

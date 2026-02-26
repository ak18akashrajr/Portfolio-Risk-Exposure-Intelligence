from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from .database import get_session, create_db_and_tables
from .models import Transaction, Holding
from .ingestion import ingest_excel, update_holdings, add_manual_transaction
from .schemas import ManualTransactionInput
from .agent import get_ai_response
from sqlmodel import select
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Portfolio Risk Exposure Intelligence API")

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        ingest_excel(temp_path)
        return {"message": "File processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/transactions/manual")
async def manual_entry(data: ManualTransactionInput, session: Session = Depends(get_session)):
    try:
        transaction = add_manual_transaction(
            session=session,
            symbol=data.symbol.upper(),
            tx_type=data.type.upper(),
            quantity=data.quantity,
            price=data.price,
            exchange=data.exchange.upper(),
            stock_name=data.stock_name,
            isin=data.isin,
            geography=data.geography,
            category=data.category,
            folio_number=data.folio_number
        )
        return {"message": "Transaction added successfully", "order_id": transaction.order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding transaction: {str(e)}")

@app.get("/transactions", response_model=List[Transaction])
def get_transactions(session: Session = Depends(get_session)):
    return session.exec(select(Transaction)).all()

import pandas as pd
from .utils import get_real_time_prices, get_valuation_history, calculate_xirr, get_valuation_history

@app.get("/valuation-history")
def valuation_history(session: Session = Depends(get_session)):
    transactions = session.exec(select(Transaction)).all()
    if not transactions:
        return []
    
    # Convert transactions to dicts for the utility function
    tx_dicts = [tx.model_dump() for tx in transactions]
    history = get_valuation_history(tx_dicts)
    return history

@app.get("/holdings", response_model=List[Holding])
def get_holdings(session: Session = Depends(get_session)):
    holdings = session.exec(select(Holding)).all()
    if not holdings:
        return []
    
    # Filter for symbols that can be fetched (primarily stocks)
    fetchable_symbols = [h.symbol for h in holdings if h.category != "Mutual Fund" or "." in h.symbol]
    live_prices = get_real_time_prices(fetchable_symbols)
    
    # Update holdings with live prices if available, otherwise keep existing
    updated_holdings = []
    for holding in holdings:
        price = live_prices.get(holding.symbol)
        if price is not None:
            holding.current_price = price
            holding.current_valuation = price * holding.quantity
            holding.last_updated_at = datetime.now()
            session.add(holding)
        elif holding.current_price is not None:
            # Preserve stale price and just update valuation if quantity changed
            holding.current_valuation = holding.current_price * holding.quantity
            # Do not update last_updated_at here as price is stale
            session.add(holding)
        updated_holdings.append(holding)
    
    session.commit()
    for h in updated_holdings:
        session.refresh(h)
        
    return updated_holdings

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Convert history to list of dicts for the agent
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
        response = get_ai_response(history_dicts)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.delete("/transactions/{order_id}")
def delete_transaction(order_id: str, session: Session = Depends(get_session)):
    transaction = session.exec(select(Transaction).where(Transaction.order_id == order_id)).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    session.delete(transaction)
    session.commit()
    update_holdings(session)
    return {"message": "Transaction deleted and holdings synced successfully"}

@app.get("/xirr-projection")
def xirr_projection(years: int = 5, session: Session = Depends(get_session)):
    transactions = session.exec(select(Transaction)).all()
    if not transactions:
        return {"xirr": 0, "projections": []}
    
    holdings = session.exec(select(Holding)).all()
    
    # Calculate current valuation
    total_valuation = 0
    fetchable_symbols = [h.symbol for h in holdings if h.category != "Mutual Fund" or "." in h.symbol]
    live_prices = get_real_time_prices(fetchable_symbols)
    
    for holding in holdings:
        price = live_prices.get(holding.symbol) or holding.current_price or 0
        total_valuation += price * holding.quantity
        
    # Prepare cash flows for XIRR
    cash_flows = []
    for tx in transactions:
        # BUY is negative cash flow (money going out)
        # SELL is positive cash flow (money coming in)
        amount = -tx.price if tx.type.upper() == "BUY" else tx.price
        cash_flows.append({"date": tx.execution_time, "amount": amount})
    
    # Add current valuation as a positive cash flow as of today
    cash_flows.append({"date": datetime.now(), "amount": total_valuation})
    
    xirr = calculate_xirr(cash_flows)
    if xirr is None:
        xirr = 0
        
    # Generate projections
    projections = []
    current_date = datetime.now()
    growth_rate = xirr if xirr > 0 else 0 # Assume 0 growth if XIRR is negative for projection
    
    # Add year 0
    projections.append({
        "date": current_date.strftime("%Y-%m-%d"),
        "value": round(total_valuation, 2)
    })
    
    for y in range(1, years + 1):
        future_date = current_date.replace(year=current_date.year + y)
        projected_value = total_valuation * ((1 + growth_rate) ** y)
        projections.append({
            "date": future_date.strftime("%Y-%m-%d"),
            "value": round(projected_value, 2)
        })
        
    return {
        "xirr": round(xirr * 100, 2), # Return as percentage
        "projections": projections
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

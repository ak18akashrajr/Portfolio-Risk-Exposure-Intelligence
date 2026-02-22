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
            category=data.category
        )
        return {"message": "Transaction added successfully", "order_id": transaction.order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding transaction: {str(e)}")

@app.get("/transactions", response_model=List[Transaction])
def get_transactions(session: Session = Depends(get_session)):
    return session.exec(select(Transaction)).all()

import pandas as pd
from .utils import get_real_time_prices, get_valuation_history

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
    
    symbols = [h.symbol for h in holdings]
    live_prices = get_real_time_prices(symbols)
    
    # Update holdings with live prices
    updated_holdings = []
    for holding in holdings:
        price = live_prices.get(holding.symbol)
        if price is not None:
            holding.current_price = price
            holding.current_valuation = price * holding.quantity
            holding.last_updated_at = datetime.now()
            session.add(holding)
        updated_holdings.append(holding)
    
    session.commit()
    # Refresh to ensure we return the latest state from DB
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

@app.get("/health")
def health_check():
    return {"status": "healthy"}

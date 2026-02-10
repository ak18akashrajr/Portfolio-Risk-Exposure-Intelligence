from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from .database import get_session, create_db_and_tables
from .models import Transaction, Holding
from .ingestion import ingest_excel
from sqlmodel import select

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

@app.get("/transactions", response_model=List[Transaction])
def get_transactions(session: Session = Depends(get_session)):
    return session.exec(select(Transaction)).all()

@app.get("/holdings", response_model=List[Holding])
def get_holdings(session: Session = Depends(get_session)):
    return session.exec(select(Holding)).all()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_name: str
    symbol: str
    isin: str
    type: str  # BUY or SELL
    quantity: float
    price: float
    exchange: str
    order_id: str = Field(index=True)
    execution_time: datetime
    geography: str = Field(default="India")
    category: str = Field(default="Equity(Stocks)")
    folio_number: Optional[str] = Field(default=None)
    status: str

class Holding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    stock_name: str
    isin: str
    quantity: float # Changed to float for MF units
    avg_price: float
    total_invested: float
    current_price: Optional[float] = Field(default=None)
    current_valuation: Optional[float] = Field(default=None)
    geography: str = Field(default="India")
    category: str = Field(default="Equity(Stocks)")
    folio_number: Optional[str] = Field(default=None)
    last_transaction_date: Optional[datetime] = None
    last_updated_at: Optional[datetime] = Field(default=None)

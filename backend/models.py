from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_name: str
    symbol: str
    isin: str
    type: str  # BUY or SELL
    quantity: int
    price: float
    exchange: str
    order_id: str = Field(index=True)
    execution_time: datetime
    geography: str = Field(default="India")
    category: str = Field(default="Equity(Stocks)")
    status: str

class Holding(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    stock_name: str
    isin: str
    quantity: int
    avg_price: float
    total_invested: float
    geography: str = Field(default="India")
    category: str = Field(default="Equity(Stocks)")
    last_transaction_date: Optional[datetime] = None

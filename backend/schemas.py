from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ManualTransactionInput(BaseModel):
    symbol: str
    type: str  # BUY or SELL
    quantity: int
    price: float  # This will be 'Value' in our context
    exchange: str
    stock_name: Optional[str] = None
    isin: Optional[str] = None
    geography: Optional[str] = "India"
    execution_time: Optional[datetime] = None

from uuid import UUID
from datetime import date, datetime
from typing import Optional, List
from sqlmodel import SQLModel

class UserBase(SQLModel):
    name: str
    email: str

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: UUID
    created_at: datetime

class PortfolioBase(SQLModel):
    name: str
    base_currency: str = "INR"

class PortfolioCreate(PortfolioBase):
    user_id: UUID

class PortfolioRead(PortfolioBase):
    id: UUID
    user_id: UUID
    created_at: datetime

class AssetBase(SQLModel):
    symbol: str
    exchange: str
    asset_type: str
    sector: Optional[str] = None
    market_cap_bucket: Optional[str] = None
    currency: str = "INR"
    geography: str = "India"

class AssetRead(AssetBase):
    id: UUID

class TransactionCreate(SQLModel):
    symbol: str
    transaction_date: date
    quantity: float
    price: float
    transaction_type: str # BUY, SELL

class TransactionRead(TransactionCreate):
    id: UUID
    portfolio_id: UUID
    asset_id: UUID
    created_at: datetime

class HoldingRead(SQLModel):
    asset_symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    pnl: float
    pnl_percentage: float

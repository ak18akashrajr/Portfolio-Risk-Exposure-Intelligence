from datetime import datetime, date
from uuid import UUID, uuid4
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

# 2. User & Portfolio

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(max_length=150, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Portfolio(SQLModel, table=True):
    __tablename__ = "portfolios"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    name: str = Field(max_length=100)
    base_currency: str = Field(default="INR", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 3. Asset Master

class Asset(SQLModel, table=True):
    __tablename__ = "assets"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    symbol: str = Field(max_length=30)  # e.g., RELIANCE.NS
    exchange: str = Field(max_length=10) # NSE, BSE
    asset_type: str = Field(max_length=30) # Equity, ETF, MF
    sector: Optional[str] = Field(default=None, max_length=50)
    market_cap_bucket: Optional[str] = Field(default=None, max_length=20)
    currency: str = Field(default="INR", max_length=10)
    geography: str = Field(default="India", max_length=30)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 4. Portfolio Transactions

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    portfolio_id: UUID = Field(foreign_key="portfolios.id")
    asset_id: UUID = Field(foreign_key="assets.id")
    transaction_date: date
    quantity: float = Field(default=0.0)
    price: float = Field(default=0.0)
    transaction_type: str = Field(max_length=10) # BUY, SELL
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 5. Holdings Snapshot

class Holding(SQLModel, table=True):
    __tablename__ = "holdings"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    portfolio_id: UUID = Field(foreign_key="portfolios.id")
    asset_id: UUID = Field(foreign_key="assets.id")
    quantity: float
    avg_cost: float
    market_value: float
    snapshot_date: date

# 6. Exposure Analytics

class Exposure(SQLModel, table=True):
    __tablename__ = "exposures"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    portfolio_id: UUID = Field(foreign_key="portfolios.id")
    exposure_type: str = Field(max_length=30) # Sector, AssetClass, etc.
    exposure_key: str = Field(max_length=50) # IT, Banking
    exposure_value: float # Percentage
    snapshot_date: date

# 7. Risk Metrics

class RiskMetric(SQLModel, table=True):
    __tablename__ = "risk_metrics"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    portfolio_id: UUID = Field(foreign_key="portfolios.id")
    volatility: Optional[float] = None
    beta: Optional[float] = None
    max_drawdown: Optional[float] = None
    var_95: Optional[float] = None
    snapshot_date: date

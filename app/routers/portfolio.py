from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from app.database import get_session
from app.schemas import PortfolioRead, TransactionCreate
from app.services.portfolio_service import add_transaction_direct, ensure_default_user_and_portfolio, ensure_asset
from app.models import Portfolio, Asset, Holding
from app.crud import get_transactions_by_portfolio
from app.services.yfinance_service import get_asset_info, get_ticker_symbol
from uuid import UUID

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.post("/init")
def init_portfolio(session: Session = Depends(get_session)):
    """
    Ensures default portfolio exists.
    """
    try:
        p = ensure_default_user_and_portfolio(session)
        return {"message": "Portfolio Initialized", "portfolio_id": p.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transaction")
def create_transaction(txn: TransactionCreate, session: Session = Depends(get_session)):
    """
    Directly adds a transaction and updates holdings
    """
    try:
        # 1. Add directly to DB
        add_transaction_direct(session, txn)
        
        return {"message": "Transaction added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{symbol}")
def search_ticker(symbol: str):
    """
    Searches for a ticker on YFinance and returns details (Price, Sector, etc.)
    """
    try:
        yf_sym = get_ticker_symbol(symbol)
        info = get_asset_info(yf_sym)
        if not info or info.get("current_price", 0) == 0:
             # Try without .NS if failed?
             if ".NS" in yf_sym:
                 info = get_asset_info(symbol)
        
        if not info:
            raise HTTPException(status_code=404, detail="Ticker not found")
            
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
def get_dashboard_data(session: Session = Depends(get_session)):
    """
    Returns aggregated data for the default portfolio from Holding table
    """
    # Get Default Portfolio
    portfolio = session.exec(select(Portfolio)).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No data found. Please refresh.")
        
    # Get Holdings from DB (populated by Importer)
    db_holdings = session.exec(select(Holding).where(Holding.portfolio_id == portfolio.id)).all()
    
    results = []
    
    # Collect equity symbols for bulk fetch
    equity_assets = [
        session.get(Asset, h.asset_id) 
        for h in db_holdings 
        if h.quantity > 0 and session.get(Asset, h.asset_id).asset_type == "Equity"
    ]
    
    # Filter valid tickers
    tickers = [a.symbol for a in equity_assets if ".NS" in a.symbol or ".BO" in a.symbol]
    
    # Bulk fetch prices
    from app.services.yfinance_service import get_bulk_current_prices
    live_prices = {}
    if tickers:
        try:
            live_prices = get_bulk_current_prices(tickers)
        except Exception as e:
            print(f"Bulk fetch failed: {e}")

    results = []
    
    for h in db_holdings:
        asset = session.get(Asset, h.asset_id)
        if not asset: continue
        
        current_price = 0
        market_val = h.market_value
        
        if asset.asset_type == "Equity":
            # Use bulk fetched price if available
            if asset.symbol in live_prices:
                current_price = live_prices[asset.symbol]
                if current_price > 0:
                    market_val = h.quantity * current_price
            # Fallback to single fetch if missed (rare) or if file value
            elif ".NS" in asset.symbol:
                 # Try single fetch as last resort? No, too slow.
                 # Just use file value
                 pass
        
        # If we couldn't get live price, verify back-calc from market_value
        if current_price == 0 and h.quantity > 0:
            current_price = h.market_value / h.quantity
            
        results.append({
            "symbol": asset.symbol,
            "type": asset.asset_type,
            "quantity": h.quantity,
            "avg_cost": h.avg_cost,
            "current_price": current_price,
            "market_value": market_val,
            "sector": asset.sector or "Unknown",
            "cap_bucket": asset.market_cap_bucket or "Unknown"
        })
            
    return {"portfolio_id": portfolio.id, "holdings": results}

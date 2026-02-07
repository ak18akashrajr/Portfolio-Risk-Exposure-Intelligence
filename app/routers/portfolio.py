from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from app.database import get_session
from app.schemas import PortfolioRead
from app.services.importer import ingest_folder
from app.models import Portfolio, Asset
from app.crud import get_transactions_by_portfolio
from app.services.yfinance_service import get_asset_info
from uuid import UUID

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.post("/refresh")
def refresh_data(session: Session = Depends(get_session)):
    """
    Triggers re-ingestion from holdings_transactions folder
    """
    try:
        portfolio_id = ingest_folder(session)
        return {"message": "Data refreshed successfully", "portfolio_id": portfolio_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
def get_dashboard_data(session: Session = Depends(get_session)):
    """
    Returns aggregated data for the default portfolio
    """
    # Get Default Portfolio (assuming single user setup)
    portfolio = session.exec(select(Portfolio)).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No data found. Please refresh.")
        
    # Calculate Holdings
    txs = get_transactions_by_portfolio(session, portfolio.id)
    holdings = {}
    
    for tx in txs:
        if tx.asset_id not in holdings:
            holdings[tx.asset_id] = {"qty": 0.0, "cost": 0.0}
        
        if tx.transaction_type == "BUY":
            holdings[tx.asset_id]["qty"] += tx.quantity
            holdings[tx.asset_id]["cost"] += (tx.quantity * tx.price)
        elif tx.transaction_type == "SELL":
            # Simplified Logic
            current_qty = holdings[tx.asset_id]["qty"] + tx.quantity
            if current_qty > 0:
                avg_cost = holdings[tx.asset_id]["cost"] / current_qty
                holdings[tx.asset_id]["cost"] -= (tx.quantity * avg_cost)
            holdings[tx.asset_id]["qty"] -= tx.quantity

    results = []
    
    # Needs optimization: Bulk fetch using YFinance service
    # Just looping for now
    for asset_id, data in holdings.items():
        if data["qty"] > 0.01: # Filter near-zero
            asset = session.get(Asset, asset_id)
            if not asset:
                continue
            
            # Live price
            curr_price = 0
            if asset.asset_type == "Equity":
                info = get_asset_info(asset.symbol)
                curr_price = info.get("current_price", 0.0)
            else:
                # Fallback implementation for MFs if live price not available
                # Use last transacted price or 0
                curr_price = data["cost"] / data["qty"] # Fallback to cost (No PnL shown)
            
            # If price fetch failed, use cost to avoid 0 value
            if curr_price == 0:
                curr_price = data["cost"] / data["qty"]

            market_val = data["qty"] * curr_price
            
            results.append({
                "symbol": asset.symbol,
                "type": asset.asset_type,
                "quantity": data["qty"],
                "avg_cost": data["cost"] / data["qty"],
                "current_price": curr_price,
                "market_value": market_val,
                "sector": asset.sector,
                "cap_bucket": asset.market_cap_bucket
            })
            
    return {"portfolio_id": portfolio.id, "holdings": results}

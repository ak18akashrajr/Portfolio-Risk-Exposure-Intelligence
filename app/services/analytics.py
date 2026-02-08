from sqlmodel import Session, select
from app.models import Portfolio, Transaction, Asset, Holding
from app.crud import get_transactions_by_portfolio, get_asset_by_symbol
from app.services.yfinance_service import get_historical_prices, get_ticker_symbol
import pandas as pd
import numpy as np
from uuid import UUID

def calculate_risk_metrics(session: Session, portfolio_id: UUID) -> dict:
    """
    Computes Volatility (Annualized), Beta (vs NIFTY 50), Max Drawdown
    """
    # Source weights from current Holdings (Snapshot)
    db_holdings = session.exec(select(Holding).where(Holding.portfolio_id == portfolio_id)).all()
    if not db_holdings:
        return {}
    
    active_holdings = {}
    for h in db_holdings:
        if h.quantity > 0:
            asset = session.get(Asset, h.asset_id)
            if asset and asset.asset_type == "Equity": # Risk only for Equity for now
                 active_holdings[asset.symbol] = h.quantity

    if not active_holdings:
        return {}
        
    # Get current prices to determine weights
    # Simplified: Assume equal weight if price fetch fails, but let's try to get prices
    # For accurate risk, we need historical prices of each asset
    
    ticker_symbols = list(active_holdings.keys())
    
    # Fetch historical data (last 1 year)
    try:
        # We need a unified DataFrame of returns
        df_prices = pd.DataFrame()
        
        for sym in ticker_symbols:
            hist = get_historical_prices(sym, period="1y")
            if not hist.empty:
                df_prices[sym] = hist['Close']
                
        if df_prices.empty:
            return {"error": "No historical data found"}
            
        # Forward fill missing data
        df_prices.fillna(method='ffill', inplace=True)
        df_prices.dropna(inplace=True)
        
        # Calculate Daily Returns
        returns = df_prices.pct_change().dropna()
        
        # Calculate Portfolio Returns (Assuming constant weights for simplicity - rebalanced daily)
        # Weight = Value / TotalValue
        # We need current value to get current weights
        curr_prices = df_prices.iloc[-1]
        
        weights = {}
        total_val = 0
        for sym in ticker_symbols:
            if sym in curr_prices:
                val = active_holdings[sym] * curr_prices[sym]
                weights[sym] = val
                total_val += val
                
        if total_val == 0:
            return {}
            
        weight_vector = np.array([weights[sym]/total_val for sym in df_prices.columns])
        
        # Portfolio Daily Returns = Dot Product of Weights and Asset Returns
        portfolio_returns = returns.dot(weight_vector)
        
        # 1. Annualized Volatility
        daily_vol = portfolio_returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # 2. Beta (vs Nifty 50)
        nifty_hist = get_historical_prices("^NSEI", period="1y") # Nifty 50
        beta = 0.0
        if not nifty_hist.empty:
            nifty_returns = nifty_hist['Close'].pct_change().dropna()
            # Align dates
            aligned_data = pd.concat([portfolio_returns, nifty_returns], axis=1).dropna()
            aligned_data.columns = ['Portfolio', 'Market']
            
            cov_matrix = aligned_data.cov()
            cov_pm = cov_matrix.loc['Portfolio', 'Market']
            var_m = cov_matrix.loc['Market', 'Market']
            beta = cov_pm / var_m
            
        # 3. Max Drawdown
        # Create wealth index
        wealth_index = (1 + portfolio_returns).cumprod()
        previous_peaks = wealth_index.cummax()
        drawdown = (wealth_index - previous_peaks) / previous_peaks
        max_drawdown = drawdown.min()
        
        return {
            "volatility": round(annual_vol * 100, 2), # %
            "beta": round(beta, 2),
            "max_drawdown": round(max_drawdown * 100, 2) # %
        }
        
    except Exception as e:
        print(f"Error calculating risk: {e}")
        return {"error": str(e)}

def run_stress_test(session: Session, portfolio_id: UUID, scenario: str) -> dict:
    """
    Simulates portfolio impact under stress scenarios
    """
    # Simplistic Beta-based estimation
    metrics = calculate_risk_metrics(session, portfolio_id)
    beta = metrics.get("beta", 1.0)
    
    impact = 0.0
    if scenario == "MARKET_CRASH_20": # Nifty -20%
        impact = -20.0 * beta
    elif scenario == "MARKET_CORRECTION_10": # Nifty -10%
        impact = -10.0 * beta
    elif scenario == "TECH_CRASH":
        # Need sector exposure for this
        pass
        
    return {
        "scenario": scenario,
        "estimated_impact_pct": round(impact, 2)
    }

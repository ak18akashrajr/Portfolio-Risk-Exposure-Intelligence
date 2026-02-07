import yfinance as yf
from datetime import date, timedelta
import pandas as pd
from typing import Optional

def get_ticker_symbol(symbol: str, exchange: str = "NSE") -> str:
    if exchange == "NSE":
        return f"{symbol}.NS"
    elif exchange == "BSE":
        return f"{symbol}.BO"
    return symbol

def get_asset_info(symbol: str) -> dict:
    """
    Fetches asset metadata: Sector, Market Cap, Current Price
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extract relevant fields
        sector = info.get("sector", "Unknown")
        market_cap = info.get("marketCap", 0)
        current_price = info.get("currentPrice", 0.0)
        industry = info.get("industry", "Unknown")
        
        # Determine Market Cap Bucket (India specific approximation)
        # Large Cap: > 20,000 Cr (~ 2.5B USD)
        # Mid Cap: 5,000 - 20,000 Cr
        # Small Cap: < 5,000 Cr
        mcap_in_cr = market_cap / 10000000
        if mcap_in_cr > 20000:
            bucket = "Large Cap"
        elif mcap_in_cr > 5000:
            bucket = "Mid Cap"
        else:
            bucket = "Small Cap"
            
        return {
            "sector": sector,
            "industry": industry,
            "market_cap": market_cap,
            "market_cap_bucket": bucket,
            "current_price": current_price,
            "currency": info.get("currency", "INR")
        }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {}

def get_historical_prices(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetches historical data for risk metrics
    """
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)
    return history

def get_bulk_current_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetches current prices for multiple symbols
    """
    if not symbols:
        return {}
    
    tickers = yf.Tickers(" ".join(symbols))
    prices = {}
    for symbol in symbols:
        try:
             # Fast way to get price?
             # accessing tickers.tickers[symbol].info might be slow loop
             # download last 1 day data
             pass
        except:
             pass
    
    # Efficient bulk download for last 1 day to get close price
    data = yf.download(symbols, period="1d", progress=False)['Close']
    
    if isinstance(data, pd.Series): # Single symbol
        prices[symbols[0]] = float(data.iloc[-1])
    else:
        # data is DataFrame with columns as symbols
        # Check if empty (e.g. all failed)
        if not data.empty:
            last_row = data.iloc[-1]
            for sym in symbols:
                 if sym in last_row:
                     prices[sym] = float(last_row[sym])
    
    return prices

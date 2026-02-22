import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def get_real_time_prices(symbols: List[str]) -> Dict[str, Optional[float]]:
    """
    Fetches real-time prices for a list of symbols using yfinance.
    Returns a dictionary mapping symbols to prices.
    """
    if not symbols:
        return {}
    
    # Pre-process symbols to append .NS if suffix is missing
    processed_symbols = []
    symbol_map = {} 
    
    for s in symbols:
        if "." not in s:
            mapped = f"{s}.NS"
        else:
            mapped = s
        processed_symbols.append(mapped)
        symbol_map[mapped] = s

    symbols_str = " ".join(processed_symbols)
    try:
        data = yf.download(symbols_str, period="1d", interval="1m", progress=False)
        prices_dict = {}
        
        if len(processed_symbols) == 1:
            mapped = processed_symbols[0]
            original = symbol_map[mapped]
            if not data.empty and 'Close' in data:
                val = data['Close'].iloc[-1]
                prices_dict[original] = float(val) if not pd.isna(val) else None
            else:
                prices_dict[original] = None
        else:
            for mapped, original in symbol_map.items():
                try:
                    if 'Close' in data and mapped in data['Close']:
                        price = data['Close'][mapped].iloc[-1]
                        prices_dict[original] = float(price) if not pd.isna(price) else None
                    else:
                        prices_dict[original] = None
                except Exception as e:
                    logger.error(f"Error extracting price for {mapped} ({original}): {e}")
                    prices_dict[original] = None
        
        return prices_dict
    except Exception as e:
        logger.error(f"Network or API Error fetching prices with yfinance: {e}")
        return {symbol: None for symbol in symbols}

def get_market_data_live(symbol: str):
    """Returns market data for a single symbol with real-time fetching."""
    prices = get_real_time_prices([symbol])
    price = prices.get(symbol)
    
    return {
        "symbol": symbol,
        "price": price,
        "currency": "INR",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "yfinance" if price else "stale",
        "status": "real-time" if price else "stale"
    }

def get_market_data_mock(symbol: str):
    """Fallback mock data for when live fetching fails."""
    return {
        "symbol": symbol,
        "price": 1000.0,
        "currency": "INR",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "mock",
        "status": "stale"
    }

def get_valuation_history(transactions: List[Dict]) -> List[Dict]:
    """
    Calculates daily portfolio valuation history.
    """
    if not transactions:
        return []

    df_tx = pd.DataFrame(transactions)
    df_tx['execution_time'] = pd.to_datetime(df_tx['execution_time'])
    
    symbols = df_tx['symbol'].unique().tolist()
    processed_symbols = [f"{s}.NS" if "." not in s else s for s in symbols]
    symbol_map = {f"{s}.NS" if "." not in s else s: s for s in symbols}
    
    start_date = df_tx['execution_time'].min().strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Fetch daily close prices
        data = yf.download(" ".join(processed_symbols), start=start_date, end=end_date, interval="1d", progress=False)
        hist_data = data['Close']
        
        if len(processed_symbols) == 1:
            hist_data = hist_data.to_frame()
            hist_data.columns = [processed_symbols[0]]
            
        hist_data = hist_data.rename(columns=symbol_map)
        hist_data = hist_data.resample('D').ffill()
        
        timeline = pd.date_range(start=start_date, end=end_date, freq='D')
        valuation_history = []
        
        for current_date in timeline:
            mask = df_tx['execution_time'] <= current_date
            past_tx = df_tx[mask]
            
            total_invested = 0
            total_valuation = 0
            
            for symbol in symbols:
                sym_tx = past_tx[past_tx['symbol'] == symbol]
                if sym_tx.empty:
                    continue
                
                qty = 0
                sym_invested = 0
                for _, tx in sym_tx.iterrows():
                    if tx['type'].upper() == 'BUY':
                        qty += tx['quantity']
                        sym_invested += tx['price'] # tx['price'] is already the total buy value
                    else:
                        # For sell, we reduce quantity and proportional cost basis
                        if qty > 0:
                            reduction_ratio = tx['quantity'] / qty
                            sym_invested *= (1 - reduction_ratio)
                        qty -= tx['quantity']
                
                total_invested += sym_invested
                
                if qty > 0:
                    price = 0
                    if symbol in hist_data.columns:
                        day_price = hist_data.loc[current_date, symbol] if current_date in hist_data.index else None
                        if pd.isna(day_price) or day_price is None:
                            valid_prices = hist_data[symbol].loc[:current_date].dropna()
                            price = valid_prices.iloc[-1] if not valid_prices.empty else 0
                        else:
                            price = day_price
                    
                    total_valuation += (qty * price)
            
            valuation_history.append({
                "date": current_date.date().isoformat(),
                "invested_value": round(float(total_invested), 2),
                "market_value": round(float(total_valuation), 2)
            })
            
        return valuation_history
    except Exception as e:
        logger.error(f"Error calculating valuation history: {e}")
        return []

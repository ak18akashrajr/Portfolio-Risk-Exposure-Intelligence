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
        # Remove interval="1m" to support Mutual Funds
        data = yf.download(symbols_str, period="1d", progress=False)
        prices_dict = {}
        
        for mapped, original in symbol_map.items():
            price = None
            try:
                # Extract from batch data
                if len(processed_symbols) == 1:
                    if not data.empty and 'Close' in data:
                        v = data['Close'].iloc[-1]
                        price = float(v) if not pd.isna(v) else None
                else:
                    if 'Close' in data and mapped in data['Close']:
                        v = data['Close'][mapped].iloc[-1]
                        price = float(v) if not pd.isna(v) else None
                
                # FALLBACK: If batch fails (common for MFs), use fast_info
                if price is None:
                    ticker = yf.Ticker(mapped)
                    f_price = ticker.fast_info.last_price
                    if f_price is not None and not pd.isna(f_price):
                        price = float(f_price)
            except Exception as e:
                logger.error(f"Error for {mapped}: {e}")
                # Individual fallback attempt
                try:
                    price = float(yf.Ticker(mapped).fast_info.last_price)
                except:
                    price = None
            
            prices_dict[original] = price
        
        return prices_dict
    except Exception as e:
        logger.error(f"Batch download failed: {e}. Falling back to individual fetches.")
        prices_dict = {}
        for mapped, original in symbol_map.items():
            try:
                prices_dict[original] = float(yf.Ticker(mapped).fast_info.last_price)
            except:
                prices_dict[original] = None
        return prices_dict

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
    # Use tomorrow as end_date to ensure we get today's data if available
    end_date = (datetime.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        # Fetch daily close prices
        data = yf.download(" ".join(processed_symbols), start=start_date, end=end_date, interval="1d", progress=False)
        hist_data = data['Close']
        
        if len(processed_symbols) == 1:
            hist_data = hist_data.to_frame()
            hist_data.columns = [processed_symbols[0]]
            
        hist_data = hist_data.rename(columns=symbol_map)
        # Forward fill and then backward fill just in case, but keep NaNs if absolutely no data
        hist_data = hist_data.ffill().bfill()
        
        # Get live prices for today's fallback
        live_prices = get_real_time_prices(symbols)
        
        today_date = datetime.now().date()
        timeline = pd.date_range(start=start_date, end=datetime.now(), freq='D')
        valuation_history = []
        
        # Keep track of last known prices per symbol to carry forward manually if needed
        last_known_prices = {s: 0.0 for s in symbols}
        
        for current_ts in timeline:
            current_date = current_ts.date()
            mask = df_tx['execution_time'] <= pd.Timestamp(current_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
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
                        sym_invested += tx['price']
                    else:
                        if qty > 0:
                            reduction_ratio = tx['quantity'] / qty
                            sym_invested *= (1 - reduction_ratio)
                        qty -= tx['quantity']
                
                total_invested += sym_invested
                
                if qty > 0:
                    price = 0
                    # Try getting price from history
                    if symbol in hist_data.columns:
                        # Find closest date in index that is <= current_date
                        valid_idx = hist_data.index[hist_data.index.date <= current_date]
                        if not valid_idx.empty:
                            hist_price = hist_data.loc[valid_idx[-1], symbol]
                            if not pd.isna(hist_price):
                                price = hist_price
                                last_known_prices[symbol] = price
                    
                    # For today, if hist is missing or we want latest, use live_prices
                    if current_date == today_date:
                        lp = live_prices.get(symbol)
                        if lp is not None:
                            price = lp
                            last_known_prices[symbol] = price
                    
                    # Final fallback: use last known
                    if price == 0 or pd.isna(price):
                        price = last_known_prices.get(symbol, 0.0)
                        
                    total_valuation += (qty * price)
            
            valuation_history.append({
                "date": current_date.isoformat(),
                "invested_value": round(float(total_invested), 2),
                "market_value": round(float(total_valuation), 2)
            })
            
        return valuation_history
    except Exception as e:
        logger.error(f"Error calculating valuation history: {e}")
        return []

def calculate_xirr(cash_flows: List[Dict[str, any]]) -> Optional[float]:
    """
    Calculates the Internal Rate of Return for a series of cash flows at irregular intervals.
    cash_flows: List of dicts with 'date' (datetime) and 'amount' (float).
    Uses the bisection method to solve for the root of the NPV function.
    """
    if not cash_flows:
        return None

    def npv(rate: float, cash_flows: List[Dict]) -> float:
        total_npv = 0
        t0 = min(cf['date'] for cf in cash_flows)
        for cf in cash_flows:
            t = (cf['date'] - t0).days / 365.0
            total_npv += cf['amount'] / ((1 + rate) ** t)
        return total_npv

    # Filter out zero cash flows
    cash_flows = [cf for cf in cash_flows if cf['amount'] != 0]
    if not cash_flows:
        return None

    # Solver parameters
    low = -0.99
    high = 10.0  # 1000% upper limit for safety
    max_iter = 100
    tol = 1e-6

    # Check for sign change
    f_low = npv(low, cash_flows)
    f_high = npv(high, cash_flows)

    if f_low * f_high > 0:
        # No root in range, try to expand high if it's potentially very high
        # Or return None if it's clearly not converging
        return None

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid, cash_flows)
        
        if abs(f_mid) < tol:
            return mid
        
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
            
    return (low + high) / 2

def format_indian_currency(amount: float) -> str:
    """
    Formats a number into Indian Numbering System (Lakh/Crore) with commas.
    Example: 1234567.89 -> 12,34,567.89
    """
    if str(amount) == 'nan' or amount is None:
        return "₹0.00"
    
    s = f"{amount:.2f}"
    if "." in s:
        integer_part, decimal_part = s.split(".")
    else:
        integer_part, decimal_part = s, "00"
    
    # Process integer part for Indian commas
    res = ""
    # Last 3 digits
    if len(integer_part) > 3:
        res = "," + integer_part[-3:]
        remaining = integer_part[:-3]
        # Groups of 2 for the rest
        while len(remaining) > 2:
            res = "," + remaining[-2:] + res
            remaining = remaining[:-2]
        res = remaining + res
    else:
        res = integer_part
    
    return f"₹{res}.{decimal_part}"

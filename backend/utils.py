import random
from datetime import datetime

# A list of common stock symbols for mock data
COMMON_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "BHARTIARTL.NS", "LICI.NS", "ITC.NS", "HINDUNILVR.NS"
]

def get_mock_price(symbol):
    """Generates a mock price for a given symbol."""
    # Seed based on symbol hash to keep it somewhat stable for a session if needed, 
    # but let's just make it reasonably random for now.
    random.seed(symbol)
    base_price = random.uniform(100, 5000)
    # Randomly change it slightly
    current_price = base_price * (1 + random.uniform(-0.02, 0.02))
    return round(current_price, 2)

def get_market_data_mock(symbol):
    """Returns mock market data for a symbol."""
    price = get_mock_price(symbol)
    return {
        "symbol": symbol,
        "price": price,
        "currency": "INR",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "mock",
        "status": "stale-data only"
    }

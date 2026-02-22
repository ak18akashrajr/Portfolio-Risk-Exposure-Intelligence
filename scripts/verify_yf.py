import sys
import os

# Add the project root to sys.path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils import get_real_time_prices

def test_price_fetching():
    symbols = ["RELIANCE.NS", "TCS.NS"]
    print(f"Fetching prices for: {symbols}")
    prices = get_real_time_prices(symbols)
    print(f"Result: {prices}")
    
    for symbol in symbols:
        if prices.get(symbol) is not None:
            print(f"[SUCCESS] Successfully fetched price for {symbol}: {prices[symbol]}")
        else:
            print(f"[FAILED] Failed to fetch price for {symbol}")

if __name__ == "__main__":
    test_price_fetching()

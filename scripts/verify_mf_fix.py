import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils import get_real_time_prices

def verify_fix():
    ticker = "0P0000YWL1.BO"
    print(f"Verifying fix for ticker: {ticker}")
    
    prices = get_real_time_prices([ticker])
    print(f"Result mapping: {prices}")
    
    price = prices.get(ticker)
    if price:
        print(f"[SUCCESS] Successfully fetched price for {ticker}: {price}")
    else:
        print(f"[FAILURE] Could not fetch price for {ticker}")

if __name__ == "__main__":
    verify_fix()

import yfinance as yf
import pandas as pd
from datetime import datetime

def test_mf_ticker():
    symbol = "0P0000YWL1.BO"
    print(f"Testing fetch for: {symbol}")
    
    # Try download method (failed for user)
    try:
        print("\n--- Testing yf.download ---")
        data = yf.download(symbol, period="1d", progress=False)
        print("Download data:")
        print(data)
    except Exception as e:
        print(f"yf.download error: {e}")

    # Try fast_info method
    try:
        print("\n--- Testing Ticker.fast_info ---")
        t = yf.Ticker(symbol)
        print("fast_info.last_price:", t.fast_info.last_price)
    except Exception as e:
        print(f"fast_info error: {e}")

    # Try history method with longer period
    try:
        print("\n--- Testing Ticker.history(period='5d') ---")
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        print("History data:")
        print(hist)
    except Exception as e:
        print(f"history error: {e}")

if __name__ == "__main__":
    test_mf_ticker()

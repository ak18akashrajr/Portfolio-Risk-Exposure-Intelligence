import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def test_hist_mf():
    symbol = "0P0000YWL1.BO"
    end = datetime.now()
    start = end - timedelta(days=10)
    
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    
    print(f"Testing yf.download for {symbol} from {start_str} to {end_str}")
    
    try:
        data = yf.download(symbol, start=start_str, end=end_str, progress=False)
        print("Download data (Close):")
        if not data.empty and 'Close' in data:
            print(data['Close'])
        else:
            print("Data is empty or missing 'Close'")
            print(data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_hist_mf()

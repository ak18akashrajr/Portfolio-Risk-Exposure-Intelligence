import yfinance as yf
import pandas as pd
from datetime import datetime

def check_hist():
    symbols = ["NIFTYBEES.NS", "GOLDBEES.NS", "BANKBEES.NS", "MON100.NS"]
    start = "2022-08-29"
    end = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Fetching data for {symbols} from {start} to {end}")
    data = yf.download(symbols, start=start, end=end, interval="1d", progress=False)['Close']
    
    print("\nData summary:")
    print(data.describe())
    print("\nNull counts:")
    print(data.isnull().sum())
    
    for s in symbols:
        if s in data.columns:
            last_price = data[s].dropna().iloc[-1] if not data[s].dropna().empty else "N/A"
            print(f"{s}: Last Price = {last_price}")
        else:
            print(f"{s}: NOT IN COLUMNS")

if __name__ == "__main__":
    check_hist()

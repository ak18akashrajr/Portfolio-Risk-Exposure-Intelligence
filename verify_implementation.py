import requests
import os

BACKEND_URL = "http://127.0.0.1:8000"
FILE_PATH = r"holdings_transactions\Stocks_Order_History_1551826140_01-04-2021_06-02-2026.xlsx"

def test_upload():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    with open(FILE_PATH, "rb") as f:
        response = requests.post(f"{BACKEND_URL}/upload", files={"file": f})
    
    print(f"Upload Status: {response.status_code}")
    print(f"Upload Response: {response.json()}")

def test_get_holdings():
    response = requests.get(f"{BACKEND_URL}/holdings")
    print(f"Holdings Status: {response.status_code}")
    if response.status_code == 200:
        holdings = response.json()
        print(f"Found {len(holdings)} holdings.")
        for h in holdings[:5]:
            print(h)

if __name__ == "__main__":
    test_upload()
    test_get_holdings()

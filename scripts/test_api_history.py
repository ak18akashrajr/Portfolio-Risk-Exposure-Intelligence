import requests
import json

def test_valuation_endpoint():
    try:
        response = requests.get("http://localhost:8000/valuation-history")
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully fetched {len(data)} history points.")
            if data:
                print("First point:", data[0])
                print("Last point:", data[-1])
        else:
            print(f"Failed to fetch data. Status: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_valuation_endpoint()

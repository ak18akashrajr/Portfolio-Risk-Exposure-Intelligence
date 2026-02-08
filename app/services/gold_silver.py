import requests
import json

def get_gold_silver_data():
    # GoldPrice public data endpoint
    url = "https://data-asg.goldprice.org/dbXRates/USD"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # ---- Safety checks ----
        if response.status_code != 200:
            return {"error": f"HTTP Error: {response.status_code}"}

        if not response.text.strip():
            return {"error": "Empty response received from server"}

        data = response.json()
        
        # ---- Extract prices ----
        item = data["items"][0]

        gold_oz_usd = float(item["xauPrice"])
        silver_oz_usd = float(item["xagPrice"])

        # Convert to per gram
        TROY_OUNCE_TO_GRAM = 31.1035

        gold_per_gram = gold_oz_usd / TROY_OUNCE_TO_GRAM
        silver_per_gram = silver_oz_usd / TROY_OUNCE_TO_GRAM

        ratio = gold_per_gram / silver_per_gram

        # ---- Decision Engine ----
        if ratio >= 70:
            decision = "Accumulate SILVER (Silver is relatively cheap)"
        elif 50 <= ratio < 70:
            decision = "Balanced accumulation (Fair value zone)"
        else:
            decision = "Accumulate GOLD (Silver is relatively expensive)"
            
        return {
            "gold_usd_per_gram": gold_per_gram,
            "silver_usd_per_gram": silver_per_gram,
            "ratio": ratio,
            "decision": decision
        }

    except json.JSONDecodeError:
        return {"error": "Response is not valid JSON. Likely blocked by Cloudflare."}
    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}

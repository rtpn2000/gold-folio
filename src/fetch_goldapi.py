# Fetches the current price of gold in INR from Gold Price API directly.

import requests
from datetime import datetime
from config import goldapi_key, ounce_to_g

SUPPORTED_METALS = {"XAU", "XAG", "XPT"}

def fetch_goldapi(symbol="XAU"):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_METALS:
        raise ValueError(f"Unsupported metal symbol: {symbol}")

    url = f"https://api.gold-api.com/price/{symbol}/INR"
    headers = {}
    if goldapi_key:
        headers["x-access-token"] = goldapi_key

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    price = data.get("price")
    if price is None:
        raise ValueError(f"Gold API did not return price for {symbol}")

    price_per_gram_inr = float(price) / ounce_to_g

    return {
        "price_per_gram_inr": round(price_per_gram_inr, 2),
        "source": f"gold-api-{symbol}",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# Printing for debugging.
if __name__ == "__main__":
    print(fetch_goldapi())
# Fetches the current price of gold in 'USD' from Gold Price API!

import requests
from datetime import datetime
from config import ounce_to_g

def fetch_goldapi():
    url = "https://api.gold-api.com/price/XAU"  # XAU = Asset code for gold.
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    # Check - If required rates are missing!
    price = data.get("price")
    if not price:
        raise ValueError("Gold API did not return price")
    
    price_per_gram = data["price"] / ounce_to_g

    return {
        "price_per_gram_usd": round(price_per_gram, 2),
        "source": "gold-api",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# Printing for debugging.
if __name__ == "__main__":
    print(fetch_goldapi())
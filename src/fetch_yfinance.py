# Predicts the current gold price in USD and INR using Yahoo Finance data!

import yfinance as yf
from datetime import datetime

# Retrieves price in USD per troy ounce, so we need to convert it to price per gram. - Gold OZ differs.
ounce_to_g = 31.1034768

def fetch_yfinance():
    # Fetch gold futures.
    gold = yf.Ticker("GC=F")
    gold_data = gold.history(period="1d")

    # Check - If required rates are missing!
    if gold_data.empty:
        raise ValueError("Yahoo Finance gold data unavailable")

    gold_usd_per_ounce = gold_data["Close"].iloc[-1]

    # USD to INR rate!
    usd_inr = fetch_usd_inr_rate()

    gold_usd_per_gram = gold_usd_per_ounce / ounce_to_g
    gold_inr_per_gram = gold_usd_per_gram * usd_inr

    return {
        "price_per_gram_usd": round(gold_usd_per_gram, 2),
        "price_per_gram_inr": round(gold_inr_per_gram, 2),
        "usd_inr_rate": round(usd_inr, 2),
        "source": "yahoo-finance",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

def fetch_usd_inr_rate():
    fx_data = yf.Ticker("INR=X").history(period="1d")
    if fx_data.empty:
        raise ValueError("Yahoo Finance USD/INR data unavailable")
    return float(fx_data["Close"].iloc[-1])

# Debug
if __name__ == "__main__":
    data = fetch_yfinance()
    print("Yahoo Gold:", data)
# Predicts the current metal price in USD and INR using Yahoo Finance data!

import yfinance as yf
from datetime import datetime

# Retrieves price in USD per troy ounce, so we need to convert it to price per gram.
ounce_to_g = 31.1034768
METAL_TICKERS = {
    "XAU": "GC=F",
    "XAG": "SI=F",
    "XPT": "PL=F",
}

def fetch_yfinance(symbol="XAU"):
    symbol = symbol.upper()
    ticker = METAL_TICKERS.get(symbol)
    if not ticker:
        raise ValueError(f"Unsupported metal symbol: {symbol}")

    metal = yf.Ticker(ticker)
    metal_data = metal.history(period="1d")

    if metal_data.empty:
        raise ValueError(f"Yahoo Finance data unavailable for {symbol}")

    metal_usd_per_ounce = metal_data["Close"].iloc[-1]
    usd_inr = fetch_usd_inr_rate()

    metal_usd_per_gram = metal_usd_per_ounce / ounce_to_g
    metal_inr_per_gram = metal_usd_per_gram * usd_inr

    return {
        "price_per_gram_usd": round(metal_usd_per_gram, 2),
        "price_per_gram_inr": round(metal_inr_per_gram, 2),
        "usd_inr_rate": round(usd_inr, 2),
        "source": f"yahoo-finance-{symbol}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
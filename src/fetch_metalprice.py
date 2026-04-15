import requests
from datetime import datetime
from config import metalprice_api_key, ounce_to_g
from src.fetch_yfinance import fetch_usd_inr_rate

SUPPORTED_METALS = {"XAU", "XAG", "XPT"}

def fetch_metalprice(symbol="XAU", api_key=metalprice_api_key):
    symbol = symbol.upper()
    if symbol not in SUPPORTED_METALS:
        raise ValueError(f"Unsupported metal symbol: {symbol}")

    url = "https://api.metalpriceapi.com/v1/latest"
    params = {
        "api_key": api_key,
        "base": "USD",
        "currencies": symbol,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    rates = data.get("rates", {})
    rate = rates.get(symbol)

    if not rate:
        raise ValueError(f"MetalPriceAPI missing {symbol} rate")

    usd_inr = fetch_usd_inr_rate()
    metal_usd_per_ounce = 1 / rate
    metal_usd_per_gram = metal_usd_per_ounce / ounce_to_g
    metal_inr_per_gram = metal_usd_per_gram * usd_inr

    return {
        "price_per_gram_inr": round(metal_inr_per_gram, 2),
        "price_per_gram_usd": round(metal_usd_per_gram, 2),
        "usd_inr_rate": round(usd_inr, 2),
        "source": f"metalpriceapi-{symbol}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

if __name__ == "__main__":
    print(fetch_metalprice())

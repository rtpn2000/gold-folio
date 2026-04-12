import requests
from datetime import datetime
from config import metalprice_api_key, ounce_to_g
from src.fetch_yfinance import fetch_usd_inr_rate

def fetch_metalprice(api_key=metalprice_api_key):
    url = "https://api.metalpriceapi.com/v1/latest"
    params = {
        "api_key": api_key,
        "base": "USD",
        "currencies": "XAU"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    rates = data.get("rates", {})
    xau_rate = rates.get("XAU")

    if not xau_rate:
        raise ValueError("MetalPriceAPI missing XAU rate")

    usd_inr = fetch_usd_inr_rate()

    gold_usd_per_ounce = 1 / xau_rate
    gold_usd_per_gram = gold_usd_per_ounce / ounce_to_g
    gold_inr_per_gram = gold_usd_per_gram * usd_inr

    return {
        "price_per_gram_inr": round(gold_inr_per_gram, 2),
        "price_per_gram_usd": round(gold_usd_per_gram, 2),
        "usd_inr_rate": round(usd_inr, 2),
        "source": "metalpriceapi",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

if __name__ == "__main__":
    print(fetch_metalprice())

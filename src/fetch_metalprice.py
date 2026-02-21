# Fetches the current price of gold in 'INR' from MetalpriceAPI!
# Delayed by 24 hours, so for benchmarking and historical data.

import requests
from datetime import datetime
from config import metalprice_api_key, ounce_to_g 

def fetch_metalprice(api_key = metalprice_api_key):

    # Fetches latest gold price from MetalpriceAPI and converts to per gram in INR.
    url = "https://api.metalpriceapi.com/v1/latest"
    params = {
        "api_key": api_key,
        "base": "USD",
        "currencies": "INR,XAU"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    rates = data.get("rates", {})

    usd_inr = rates.get("INR")
    xau_rate = rates.get("XAU")

    # Check - If required rates are missing!
    if not usd_inr or not xau_rate:
        raise ValueError("MetalPriceAPI missing required rates")

    # Conversion.
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


# Printing for debugging.
if __name__ == "__main__":
    print(fetch_metalprice())
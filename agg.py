# Aggregation module to fetch gold prices from multiple APIs and return the original prices.

from src.fetch_goldapi import fetch_goldapi
from src.fetch_metalprice import fetch_metalprice
from config import metalprice_api_key

def aggregate_gold_prices():
    results = []

    # GoldAPI
    try:
        goldapi_data = fetch_goldapi()
        results.append(goldapi_data)
    except Exception as e:
        print(f"[GoldAPI Error] {e}")

    # MetalPriceAPI
    try:
        metalprice_data = fetch_metalprice()
        results.append(metalprice_data)
    except Exception as e:
        print(f"[MetalPriceAPI Error] {e}")

    if not results:
        return {"error": "No data available from APIs."}

    # Returning the original prices.
    return {
        "prices": results,
        "sources": [r["source"] for r in results],
        "timestamp": results[-1]["timestamp"]
    }
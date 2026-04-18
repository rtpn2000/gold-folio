from src.fetch_goldapi import fetch_goldapi
from src.fetch_metalprice import fetch_metalprice


def aggregate_gold_prices(symbol="XAU"):
    symbol = symbol.upper()
    usd_data = None
    inr_data = None
    sources = []
    prices = []

    try:
        usd_data = fetch_metalprice(symbol=symbol)
        sources.append(usd_data.get("source", "metalpriceapi"))
        prices.append({
            "price_per_gram_usd": usd_data.get("price_per_gram_usd"),
            "source": usd_data.get("source"),
            "timestamp": usd_data.get("timestamp"),
        })
    except Exception as e:
        print(f"[MetalPriceAPI Error] {e}")

    try:
        inr_data = fetch_goldapi(symbol=symbol)
        sources.append(inr_data.get("source", "gold-api"))
        prices.append({
            "price_per_gram_inr": inr_data.get("price_per_gram_inr"),
            "source": inr_data.get("source"),
            "timestamp": inr_data.get("timestamp"),
        })
    except Exception as e:
        print(f"[GoldAPI Error] {e}")

    if not prices:
        return {"error": "No data available from configured gold price sources."}

    if inr_data is None and usd_data is not None and usd_data.get("price_per_gram_inr") is not None:
        prices.append({
            "price_per_gram_inr": usd_data.get("price_per_gram_inr"),
            "source": "metalpriceapi-fallback",
            "timestamp": usd_data.get("timestamp")
        })
        sources.append("metalpriceapi-fallback")

    timestamp = None
    if inr_data is not None:
        timestamp = inr_data.get("timestamp")
    elif usd_data is not None:
        timestamp = usd_data.get("timestamp")

    return {
        "prices": prices,
        "sources": sources,
        "timestamp": timestamp
    }
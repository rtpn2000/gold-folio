from src.fetch_yfinance import fetch_yfinance


def aggregate_gold_prices(symbol="XAU"):
    symbol = symbol.upper()
    try:
        data = fetch_yfinance(symbol=symbol)
    except Exception as e:
        print(f"[Yahoo Finance Error] {e}")
        return {"error": "No data available from Yahoo Finance."}

    return {
        "prices": [{
            "price_per_gram_usd": data.get("price_per_gram_usd"),
            "price_per_gram_inr": data.get("price_per_gram_inr"),
            "usd_inr_rate": data.get("usd_inr_rate"),
            "source": data.get("source"),
            "timestamp": data.get("timestamp"),
        }],
        "sources": [data.get("source", f"yahoo-finance-{symbol}")],
        "timestamp": data.get("timestamp"),
    }

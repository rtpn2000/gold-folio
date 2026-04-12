from src.fetch_yfinance import fetch_yfinance

def aggregate_gold_prices():
    try:
        yfinance_data = fetch_yfinance()
        return {
            "prices": [yfinance_data],
            "sources": [yfinance_data["source"]],
            "timestamp": yfinance_data["timestamp"]
        }
    except Exception as e:
        print(f"[Yahoo Finance Error] {e}")
        return {"error": "No data available from Yahoo Finance."}
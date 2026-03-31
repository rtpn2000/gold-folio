from datetime import datetime

import pandas as pd
import yfinance as yf

from src.crud import upsert_gold_prices
from src.database import SessionLocal


OUNCE_TO_GRAMS = 31.1035
YF_TICKER = "GC=F"


def fetch_yfinance():
    gold = yf.Ticker(YF_TICKER)
    gold_data = gold.history(period="1d")

    if gold_data.empty:
        raise ValueError("Yahoo Finance gold data unavailable")

    gold_usd_per_ounce = gold_data["Close"].iloc[-1]

    usd_inr = yf.Ticker("INR=X").history(period="1d")["Close"].iloc[-1]

    gold_usd_per_gram = gold_usd_per_ounce / OUNCE_TO_GRAMS
    gold_inr_per_gram = gold_usd_per_gram * usd_inr

    return {
        "price_per_gram_usd": round(gold_usd_per_gram, 2),
        "price_per_gram_inr": round(gold_inr_per_gram, 2),
        "usd_inr_rate": round(float(usd_inr), 2),
        "source": "yahoo-finance",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def build_yfinance_history_records(start: str = "2023-01-01") -> list[dict]:
    yf_df = yf.download(
        YF_TICKER,
        start=start,
        auto_adjust=False,
        progress=False,
    )

    if yf_df.empty:
        raise ValueError(f"No data returned from Yahoo Finance for {YF_TICKER}")

    yf_df = yf_df.reset_index()

    if isinstance(yf_df.columns, pd.MultiIndex):
        yf_df.columns = [c[0] if isinstance(c, tuple) else c for c in yf_df.columns]

    yf_df = yf_df[["Date", "Close"]].copy()
    yf_df = yf_df.rename(columns={"Date": "date", "Close": "price_per_ounce_usd"})
    yf_df["price_per_ounce_usd"] = pd.to_numeric(yf_df["price_per_ounce_usd"], errors="coerce")
    yf_df = yf_df.dropna(subset=["date", "price_per_ounce_usd"]).copy()

    yf_df["price_per_gram_usd"] = yf_df["price_per_ounce_usd"] / OUNCE_TO_GRAMS
    yf_df["price_per_gram_inr"] = None
    yf_df["date"] = pd.to_datetime(yf_df["date"]).dt.date

    yf_df = (
        yf_df[["date", "price_per_gram_usd", "price_per_gram_inr"]]
        .sort_values("date")
        .drop_duplicates(subset=["date"])
    )

    return yf_df.to_dict(orient="records")


def insert_yfinance_history(start: str = "2023-01-01"):
    records = build_yfinance_history_records(start=start)

    db = SessionLocal()
    try:
        count = upsert_gold_prices(db, records)
    finally:
        db.close()

    return {
        "upserted": count,
        "rows_prepared": len(records),
        "first_date": str(records[0]["date"]) if records else None,
        "last_date": str(records[-1]["date"]) if records else None,
        "source": "yahoo-finance",
    }


if __name__ == "__main__":
    result = insert_yfinance_history()
    print(result)
